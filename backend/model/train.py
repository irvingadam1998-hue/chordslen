"""Reproducible supervised training. Checkpoints remain experimental by default."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import random
from time import perf_counter
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, RandomSampler, Subset
from .config import Config, fingerprint
from .dataset import ChordDataset, load_manifest, prepare_tracks, training_statistics
from .features import FEATURE_VERSION, file_digest
from .labels import IGNORE, NO_CHORD, QUALITIES
from .model import ChordModel

HEADS = ('root', 'quality', 'presence', 'bass')
CLASSES = (12, len(QUALITIES), 2, 12)
CHECKPOINT_VERSION = 1


def class_counts(tracks):
    counts = [np.zeros(n, dtype=np.int64) for n in CLASSES]
    for track in tracks:
        if track['row']['split'] == 'train':
            for i, size in enumerate(CLASSES):
                values = track['labels'][:, i]
                counts[i] += np.bincount(values[values >= 0], minlength=size)
    return counts


def chord_targets(y):
    """Joint state per frame: root * len(QUALITIES) + quality, NO_CHORD, or IGNORE."""
    root, quality, presence = y[..., 0], y[..., 1], y[..., 2]
    state = torch.full_like(root, IGNORE)
    chord = (presence == 1) & (root >= 0) & (quality >= 0)
    state[chord] = root[chord] * len(QUALITIES) + quality[chord]
    state[presence == 0] = NO_CHORD
    return state


def losses_for(counts, weighted, device):
    losses, head_weights = {}, {}
    for head, count in zip(HEADS, counts):
        weights = None
        if weighted:
            # Inverse sqrt, bounded; absent classes receive no artificial observations.
            weights = np.ones(len(count), dtype=np.float32)
            seen = count > 0
            if seen.any():
                weights[seen] = np.clip(np.sqrt(count[seen].mean() / count[seen]), 0.25, 4)
            head_weights[head] = weights
            weights = torch.tensor(weights, device=device)
        losses[head] = nn.CrossEntropyLoss(weight=weights, ignore_index=IGNORE)
    chord_weights = None
    if weighted:
        # Quality weights shared by every root: transposition mixes roots during training.
        chord_weights = torch.tensor(np.r_[np.tile(head_weights['quality'], 12), head_weights['presence'][0]],
                                     dtype=torch.float32, device=device)
    losses['chord'] = nn.CrossEntropyLoss(weight=chord_weights, ignore_index=IGNORE)
    return losses


def combined_loss(outputs, targets, losses, bass_weight):
    components = {}
    for i, name in enumerate(HEADS):
        if name in outputs and (targets[..., i] != IGNORE).any():
            components[name] = losses[name](outputs[name].flatten(0, 1), targets[..., i].flatten())
    if 'chord' in outputs:
        states = chord_targets(targets)
        if (states != IGNORE).any():
            components['chord'] = losses['chord'](outputs['chord'].flatten(0, 1), states.flatten())
    if not components:
        raise ValueError('Batch sin ninguna etiqueta válida')
    return sum(value * (bass_weight if name == 'bass' else 1) for name, value in components.items())


def run_epoch(model, loader, device, losses, cfg, optimizer=None, scaler=None):
    model.train(optimizer is not None)
    total_loss = 0.0
    correct, count = 0, 0
    for x, y, lengths in loader:
        x, y = x.to(device), y.to(device)
        with torch.set_grad_enabled(optimizer is not None):
            with torch.autocast(device_type=device.type, enabled=cfg.amp and device.type == 'cuda'):
                outputs = model(x, lengths)
                loss = combined_loss(outputs, y, losses, cfg.bass_loss_weight)
            if not torch.isfinite(loss):
                raise FloatingPointError('Pérdida no finita; entrenamiento detenido')
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                scaler.step(optimizer)
                scaler.update()
        valid = (y[..., 2] == 0) | ((y[..., 0] >= 0) & (y[..., 1] >= 0))
        if 'chord' in outputs:
            matches = outputs['chord'].argmax(-1) == chord_targets(y)
        else:
            present = outputs['presence'].argmax(-1)
            matches = ((present == 0) & (y[..., 2] == 0)) | (
                (present == 1) & (y[..., 2] == 1) & (outputs['root'].argmax(-1) == y[..., 0])
                & (outputs['quality'].argmax(-1) == y[..., 1]))
        correct += int((valid & matches).sum())
        count += int(valid.sum())
        total_loss += float(loss.detach()) * len(x)
    samples = len(loader.sampler)  # num_samples when an epoch draws a random subset
    return {'loss': total_loss / samples,
            'chord_frame_accuracy': correct / count if count else None, 'scored_frames': count}


def save_checkpoint(path, checkpoint):
    temporary = path.with_suffix('.tmp')
    torch.save(checkpoint, temporary)
    temporary.replace(path)


def train(args):
    cfg = Config.load(args.config)
    if args.epochs is not None:
        cfg.train.num_epochs = args.epochs
    if args.epochs is not None and args.epochs < 1:
        raise ValueError('--epochs debe ser positivo')
    torch.set_num_threads(cfg.train.cpu_threads)
    random.seed(cfg.train.seed)
    np.random.seed(cfg.train.seed)
    torch.manual_seed(cfg.train.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(cfg.train.seed)
    device = torch.device('cuda' if args.device == 'auto' and torch.cuda.is_available()
                          else 'cpu' if args.device == 'auto' else args.device)
    if device.type == 'cuda' and not torch.cuda.is_available():
        raise ValueError('CUDA no está disponible en este entorno')
    rows = load_manifest(args.manifest)
    # Test audio/annotations never contribute to features, normalization or selection.
    train_rows = [r for r in rows if r['split'] in {'train', 'validation'}]
    provenance = [{**{k: r[k] for k in ('id', 'artist_id', 'origin_id', 'split')},
                   'audio_sha256': file_digest(r['audio']), 'annotation_sha256': file_digest(r['annotation'])}
                  for r in train_rows]
    data_signature = fingerprint(provenance)
    tracks = prepare_tracks(train_rows, cfg.features, args.cache)
    mean, std = training_statistics(tracks)
    frames = round(cfg.train.segment_seconds * cfg.features.sample_rate / cfg.features.hop_length)
    # Augmentation only in train: validation must measure the real recordings.
    datasets = {split: ChordDataset(tracks, split, frames, mean, std, cfg.features,
                                    cfg.train.pitch_shift if split == 'train' else 0)
                for split in ('train', 'validation')}
    generator = torch.Generator().manual_seed(cfg.train.seed)
    validation = datasets['validation']
    if 0 < cfg.train.validation_segments < len(validation):
        # Fixed across epochs, so validation loss stays comparable for early stopping.
        chosen = np.random.default_rng(cfg.train.seed).choice(len(validation), cfg.train.validation_segments,
                                                             replace=False)
        validation = Subset(validation, sorted(chosen.tolist()))
    sampler = None
    if 0 < cfg.train.segments_per_epoch < len(datasets['train']):
        sampler = RandomSampler(datasets['train'], num_samples=cfg.train.segments_per_epoch, generator=generator)
    common = {'batch_size': cfg.train.batch_size, 'num_workers': cfg.train.num_workers,
              'pin_memory': device.type == 'cuda'}
    loaders = {'train': DataLoader(datasets['train'], shuffle=sampler is None, sampler=sampler,
                                   generator=generator, **common),
               'validation': DataLoader(validation, **common)}
    counts = class_counts(tracks)
    if counts[0].sum() == 0 or counts[1].sum() == 0:
        raise ValueError('No hay supervisión válida de root + quality')
    model = ChordModel(cfg.features.dimensions, cfg.model).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.train.learning_rate, weight_decay=cfg.train.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=2, factor=0.5)
    scaler = torch.amp.GradScaler('cuda', enabled=cfg.train.amp and device.type == 'cuda')
    losses = losses_for(counts, cfg.train.class_weighting, device)
    start, best, bad_epochs = 0, float('inf'), 0
    previous = None
    if args.resume:
        previous = torch.load(args.resume, map_location='cpu', weights_only=True)
        comparable = cfg.to_dict()
        comparable['train']['num_epochs'] = previous['config']['train']['num_epochs']
        # Fill defaults for fields added after the checkpoint was written.
        if (previous.get('version') != CHECKPOINT_VERSION
                or Config.from_dict(previous['config']).to_dict() != comparable
                or previous['data_signature'] != data_signature):
            raise ValueError('Checkpoint/config/datos incompatibles para reanudar')
        model.load_state_dict(previous['model'])
        optimizer.load_state_dict(previous['optimizer'])
        scheduler.load_state_dict(previous['scheduler'])
        scaler.load_state_dict(previous['scaler'])
        mean, std = np.array(previous['mean'], np.float32), np.array(previous['std'], np.float32)
        for dataset in datasets.values():
            dataset.mean, dataset.std = mean, std
        start, best, bad_epochs = previous['epoch'] + 1, previous['best_loss'], previous['bad_epochs']
        torch.set_rng_state(previous['rng_torch'])
        generator.set_state(previous['rng_loader'])
        random.setstate(previous['rng_python'])
        state = previous['rng_numpy']
        np.random.set_state((state[0], np.array(state[1], dtype=np.uint32), *state[2:]))
        if device.type == 'cuda' and previous.get('rng_cuda'):
            torch.cuda.set_rng_state_all(previous['rng_cuda'])
    args.output.mkdir(parents=True, exist_ok=True)
    if not args.resume and (args.output / 'last.pt').exists():
        raise ValueError('El directorio ya contiene un entrenamiento; usa --resume o uno nuevo')
    if args.resume and Path(args.resume).resolve().parent != args.output.resolve():
        raise ValueError('--resume debe usar el mismo directorio --output para conservar best.pt y logs')
    (args.output / 'config.json').write_text(json.dumps(cfg.to_dict(), indent=2))
    support = {name: count.tolist() for name, count in zip(HEADS, counts)}
    (args.output / 'support.json').write_text(json.dumps(support, indent=2))
    print(json.dumps({'device': str(device), 'parameters': sum(p.numel() for p in model.parameters()),
                      'segments': {k: len(v) for k, v in datasets.items()},
                      'segments_per_epoch': {k: len(v.sampler) for k, v in loaders.items()}, 'train_class_frames': support}), flush=True)
    for epoch in range(start, cfg.train.num_epochs):
        started = perf_counter()
        training = run_epoch(model, loaders['train'], device, losses, cfg.train, optimizer, scaler)
        validation = run_epoch(model, loaders['validation'], device, losses, cfg.train)
        scheduler.step(validation['loss'])
        improved = validation['loss'] < best - 1e-6
        best = min(best, validation['loss'])
        bad_epochs = 0 if improved else bad_epochs + 1
        record = {'epoch': epoch + 1, 'train': training, 'validation': validation,
                  'learning_rate': optimizer.param_groups[0]['lr'], 'seconds': perf_counter() - started}
        with (args.output / 'training.jsonl').open('a') as log:
            log.write(json.dumps(record) + '\n')
        print(json.dumps(record), flush=True)
        numpy_state = np.random.get_state()
        checkpoint = {'version': CHECKPOINT_VERSION, 'feature_version': FEATURE_VERSION,
                      'trained': True, 'production_ready': False, 'epoch': epoch, 'config': cfg.to_dict(),
                      'qualities': list(QUALITIES), 'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                      'scheduler': scheduler.state_dict(), 'scaler': scaler.state_dict(), 'best_loss': best,
                      'bad_epochs': bad_epochs, 'mean': mean.tolist(), 'std': std.tolist(),
                      'bass_supervised': bool(cfg.model.bass_head and counts[3].sum()), 'support': support,
                      'provenance': provenance, 'data_signature': data_signature, 'metrics': record,
                      'rng_torch': torch.get_rng_state(), 'rng_loader': generator.get_state(),
                      'rng_python': random.getstate(),
                      'rng_numpy': [numpy_state[0], numpy_state[1].tolist(), *numpy_state[2:]],
                      'rng_cuda': torch.cuda.get_rng_state_all() if device.type == 'cuda' else [],
                      'torch_version': str(torch.__version__)}
        save_checkpoint(args.output / 'last.pt', checkpoint)
        if improved:
            save_checkpoint(args.output / 'best.pt', checkpoint)
        if bad_epochs >= cfg.train.patience:
            print(f'Early stopping tras {epoch + 1} épocas', flush=True)
            break
    print('Modelo experimental guardado. Evalúalo antes de habilitarlo en la aplicación.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('data/manifest.jsonl'))
    parser.add_argument('--config', type=Path, default=Path(__file__).parent / 'configs/prototype.json')
    parser.add_argument('--cache', type=Path, default=Path('data/features'))
    parser.add_argument('--output', type=Path, default=Path('experiments/prototype'))
    parser.add_argument('--resume', type=Path)
    parser.add_argument('--epochs', type=int)
    parser.add_argument('--device', choices=('auto', 'cpu', 'cuda'), default='auto')
    train(parser.parse_args())


if __name__ == '__main__':
    main()

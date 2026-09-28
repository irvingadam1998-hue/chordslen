"""Explicit local promotion after a complete validation comparison; never deploys."""
import argparse
import json
from pathlib import Path
import torch
from .config import Config
from .features import file_digest
from .train import save_checkpoint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if (report.get('split') != 'validation' or not report.get('complete') or not report.get('viterbi')
            or report.get('checkpoint_sha256') != file_digest(args.checkpoint)
            or not report.get('neural', {}).get('available')):
        parser.error('Se requiere evaluación completa de validación de este mismo checkpoint')
    baseline, candidate = report['current'], report['neural']
    if (not baseline.get('available') or not baseline['songs'] or baseline['songs'] != candidate['songs']
            or not baseline['vocabulary_coverage'] or not candidate['vocabulary_coverage']):
        parser.error('Comparación sin pares suficientes o sin cobertura evaluable')
    for metric in ('weighted_chord_accuracy', 'root_accuracy', 'quality_accuracy'):
        if candidate[metric] is None or baseline[metric] is None or candidate[metric] < baseline[metric]:
            parser.error(f'No promover: regresión o ausencia de {metric}')
    if candidate['weighted_chord_accuracy'] <= baseline['weighted_chord_accuracy']:
        parser.error('No promover: no hay mejora de weighted_chord_accuracy')
    if candidate['changes']['f1'] < baseline['changes']['f1']:
        parser.error('No promover: regresión en cambios F1')
    if args.output.exists():
        parser.error('La salida ya existe; usa una ruta nueva')
    checkpoint = torch.load(args.checkpoint, map_location='cpu', weights_only=True)
    # evaluate.py --switch-cost may tune decoding; the promoted file must decode as evaluated.
    trained = Config.from_dict(checkpoint['config']).to_dict()
    evaluated = Config.from_dict(report['config']).to_dict()
    if {k: v for k, v in trained.items() if k != 'decode'} != {k: v for k, v in evaluated.items() if k != 'decode'}:
        parser.error('La configuración evaluada no corresponde a este checkpoint')
    checkpoint['config'] = {**trained, 'decode': evaluated['decode']}
    checkpoint['production_ready'] = True
    checkpoint['promotion'] = {'validation_report_sha256': file_digest(args.report),
                               'source_checkpoint_sha256': file_digest(args.checkpoint),
                               'mode': report['mode'], 'songs': candidate['songs'],
                               'decode': evaluated['decode'],
                               'weighted_chord_accuracy': candidate['weighted_chord_accuracy']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_checkpoint(args.output, checkpoint)
    print(f'Candidato habilitable guardado en {args.output}. No se cambió ni desplegó la aplicación.')


if __name__ == '__main__':
    main()

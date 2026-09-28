"""Frequency-aware CNN with interchangeable temporal context and factorized heads."""
import math
import torch
from torch import nn
from .labels import NO_CHORD, QUALITIES


class ChordModel(nn.Module):
    def __init__(self, feature_dimensions, cfg):
        super().__init__()
        self.cfg = cfg
        channels = cfg.channels
        self.encoder = nn.Sequential(
            nn.Conv2d(1, channels, 3, padding=1), nn.GELU(), nn.MaxPool2d((2, 1)),
            nn.Conv2d(channels, channels * 2, 3, padding=1), nn.GELU(), nn.MaxPool2d((2, 1)))
        # Flatten frequency, not time: absolute pitch position must remain available.
        self.projection = nn.Sequential(nn.Linear(channels * 2 * (feature_dimensions // 4), cfg.embedding),
                                        nn.LayerNorm(cfg.embedding), nn.GELU(), nn.Dropout(cfg.dropout))
        if cfg.temporal == 'bilstm':
            self.temporal = nn.LSTM(cfg.embedding, cfg.embedding // 2, num_layers=cfg.layers,
                                    bidirectional=True, batch_first=True,
                                    dropout=cfg.dropout if cfg.layers > 1 else 0)
        elif cfg.temporal == 'transformer':
            layer = nn.TransformerEncoderLayer(cfg.embedding, cfg.heads, cfg.embedding * 4,
                                               dropout=cfg.dropout, batch_first=True, norm_first=True)
            self.temporal = nn.TransformerEncoder(layer, cfg.layers, enable_nested_tensor=False)
        else:
            self.temporal = nn.Identity()
        if cfg.head == 'joint':
            # Quality is judged together with its root, e.g. the third above that root.
            self.chord = nn.Linear(cfg.embedding, NO_CHORD + 1)
        else:
            self.root = nn.Linear(cfg.embedding, 12)
            self.quality = nn.Linear(cfg.embedding, len(QUALITIES))
            self.presence = nn.Linear(cfg.embedding, 2)
        self.bass = nn.Linear(cfg.embedding, 12) if cfg.bass_head else None

    def forward(self, features, lengths=None):
        x = self.encoder(features.unsqueeze(1)).permute(0, 3, 1, 2).flatten(2)
        x = self.projection(x)
        if self.cfg.temporal == 'bilstm':
            if lengths is not None:
                packed = nn.utils.rnn.pack_padded_sequence(x, lengths.cpu(), batch_first=True, enforce_sorted=False)
                x, _ = self.temporal(packed)
                x, _ = nn.utils.rnn.pad_packed_sequence(x, batch_first=True, total_length=features.shape[-1])
            else:
                x, _ = self.temporal(x)
        elif self.cfg.temporal == 'transformer':
            positions = torch.arange(x.shape[1], device=x.device, dtype=torch.float32)[:, None]
            frequency = torch.exp(torch.arange(0, x.shape[2], 2, device=x.device) * (-math.log(10000) / x.shape[2]))
            encoding = torch.zeros(x.shape[1], x.shape[2], device=x.device)
            encoding[:, 0::2], encoding[:, 1::2] = torch.sin(positions * frequency), torch.cos(positions * frequency)
            mask = None if lengths is None else torch.arange(x.shape[1], device=x.device)[None] >= lengths.to(x.device)[:, None]
            x = self.temporal(x + encoding.to(x.dtype), src_key_padding_mask=mask)
        if self.cfg.head == 'joint':
            outputs = {'chord': self.chord(x)}
        else:
            outputs = {'root': self.root(x), 'quality': self.quality(x), 'presence': self.presence(x)}
        if self.bass is not None:
            outputs['bass'] = self.bass(x)
        return outputs

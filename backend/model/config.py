"""Versioned configuration shared by training and inference."""
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path

VOCABULARIES = ('full', 'triads')


@dataclass
class FeatureConfig:
    sample_rate: int = 22050
    hop_length: int = 512
    representation: str = 'cqt'
    bins_per_octave: int = 36
    octaves: int = 7
    fmin: float = 32.7031956626
    n_fft: int = 2048
    n_mels: int = 128
    chroma: bool = False
    bass: bool = False
    harmonic: bool = False
    block_seconds: float = 20.0

    def validate(self):
        if self.representation not in {'cqt', 'chroma', 'mel', 'stft'}:
            raise ValueError('representation debe ser cqt, chroma, mel o stft')
        if self.sample_rate < 8000 or self.hop_length <= 0 or self.block_seconds < 2:
            raise ValueError('sample_rate, hop_length o block_seconds inválidos')
        if self.bins_per_octave % 12 or not 1 <= self.octaves <= 8:
            raise ValueError('CQT requiere bins_per_octave múltiplo de 12 y 1–8 octavas')
        if self.hop_length % (2 ** (self.octaves - 1)):
            raise ValueError('hop_length incompatible con el número de octavas CQT')
        if self.fmin <= 0 or self.fmin * 2 ** self.octaves >= self.sample_rate / 2:
            raise ValueError('La CQT excede Nyquist')

    @property
    def dimensions(self):
        base = {'cqt': self.bins_per_octave * self.octaves, 'chroma': 12,
                'mel': self.n_mels, 'stft': self.n_fft // 2 + 1}[self.representation]
        return base + 12 * int(self.chroma) + 12 * int(self.bass)


@dataclass
class ModelConfig:
    temporal: str = 'none'
    channels: int = 16
    embedding: int = 96
    layers: int = 2
    heads: int = 4
    dropout: float = 0.15
    bass_head: bool = False
    # factorized: root/quality/presence heads; joint: one softmax over every chord + N.
    head: str = 'factorized'


@dataclass
class TrainConfig:
    batch_size: int = 8
    learning_rate: float = 0.001
    num_epochs: int = 40
    segment_seconds: float = 4.0
    patience: int = 8
    num_workers: int = 0
    seed: int = 42
    amp: bool = True
    class_weighting: bool = True
    bass_loss_weight: float = 0.5
    weight_decay: float = 0.0001
    cpu_threads: int = 2
    # Random transposition in [-pitch_shift, +pitch_shift] semitones; 0 disables it.
    pitch_shift: int = 0
    # 0 uses every segment. Otherwise each epoch draws this many train segments at random,
    # and validation uses a fixed random subset of validation_segments.
    segments_per_epoch: int = 0
    validation_segments: int = 0


@dataclass
class DecodeConfig:
    switch_cost: float = 2.0
    key_prior_weight: float = 0.0
    bass_threshold: float = 0.8
    bass_min_seconds: float = 0.12
    # full: every trained quality; triads: sevenths are folded into their triad.
    vocabulary: str = 'full'
    # chords: key from the model's own chord probabilities; spectrum: from the audio chroma.
    key_source: str = 'chords'


@dataclass
class Config:
    features: FeatureConfig = field(default_factory=FeatureConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
    decode: DecodeConfig = field(default_factory=DecodeConfig)

    @classmethod
    def from_dict(cls, value):
        unknown = set(value) - {'features', 'model', 'train', 'decode'}
        if unknown:
            raise ValueError(f'Configuración desconocida: {sorted(unknown)}')
        result = cls(**{key: typ(**value.get(key, {})) for key, typ in (
            ('features', FeatureConfig), ('model', ModelConfig),
            ('train', TrainConfig), ('decode', DecodeConfig))})
        result.features.validate()
        if result.model.temporal not in {'none', 'bilstm', 'transformer'}:
            raise ValueError('temporal debe ser none, bilstm o transformer')
        if result.model.head not in {'factorized', 'joint'}:
            raise ValueError('head debe ser factorized o joint')
        if result.model.embedding % 2 or result.model.embedding % result.model.heads:
            raise ValueError('embedding debe ser par y divisible por heads')
        if not 0 <= result.model.dropout < 1 or min(result.model.channels, result.model.layers) < 1:
            raise ValueError('Arquitectura inválida')
        if min(result.train.batch_size, result.train.num_epochs, result.train.patience,
               result.train.cpu_threads) < 1 or result.train.segment_seconds < 1:
            raise ValueError('Configuración de entrenamiento inválida')
        if result.train.learning_rate <= 0 or result.train.num_workers < 0:
            raise ValueError('learning_rate/num_workers inválidos')
        if min(result.train.segments_per_epoch, result.train.validation_segments) < 0:
            raise ValueError('segments_per_epoch y validation_segments deben ser >= 0')
        if not 0 <= result.train.pitch_shift <= 6:
            raise ValueError('pitch_shift debe estar entre 0 y 6 semitonos')
        if result.train.pitch_shift and result.features.representation not in {'cqt', 'chroma'}:
            raise ValueError('pitch_shift requiere representation cqt o chroma')
        if result.decode.key_source not in {'chords', 'spectrum'}:
            raise ValueError('key_source debe ser chords o spectrum')
        if result.decode.key_prior_weight < 0:
            raise ValueError('key_prior_weight debe ser no negativo')
        if result.decode.vocabulary not in VOCABULARIES:
            raise ValueError('vocabulary debe ser full o triads')
        if result.decode.switch_cost < 0 or not 0 <= result.decode.bass_threshold <= 1:
            raise ValueError('Configuración temporal inválida')
        return result

    @classmethod
    def load(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text()))

    def to_dict(self):
        return asdict(self)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

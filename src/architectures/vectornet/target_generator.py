import torch
import torch.nn as nn
from typing import Tuple, Union

from architectures.vectornet.context import VectorNet


class TargetGenerator(nn.Module):
    def __init__(self, polyline_features: int, device: Union[str, torch.device]):
        """
        Generates multiple targets from given anchor points sampled from centerlines

        Args:
            polyline_features: Number of features per polyline point
        """
        super(TargetGenerator, self).__init__()
        self._vectornet = VectorNet(polyline_features, device=device)
        self._bn_corr1 = nn.BatchNorm1d(128)
        self._bn_conf1 = nn.BatchNorm1d(128)

        # back
        self._linear1 = nn.Linear(128, 256)
        self._linear2 = nn.Linear(258, 64)

        # corrections
        self._l_corrections1 = nn.Linear(64, 128)
        self._l_corrections2 = nn.Linear(128, 2)

        # confidences
        self._l_confidence1 = nn.Linear(64, 128)
        self._l_confidence2 = nn.Linear(128, 1)

        self._relu = nn.ReLU()

    def forward(self, inputs: torch.Tensor, anchors: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        n_anchors = anchors.shape[0]

        # extract features using vectornet
        features = self._vectornet(inputs)
        features = self._relu(self._linear1(features))

        # merge anchor points with features
        expanded_features = features.repeat(n_anchors, 1)
        target_features = self._relu(self._linear2(torch.concat([expanded_features, anchors], dim=-1)))

        # Generate corrections and confidences
        corrections = self._l_corrections2(self._relu(self._bn_corr1(self._l_corrections1(target_features))))
        targets = anchors + corrections  # residual
        confidences = self._l_confidence2(self._relu(self._bn_conf1(self._l_confidence1(target_features)))).squeeze(-1)

        return features, targets, confidences


def main():
    tg = TargetGenerator(polyline_features=9, device='cpu')
    polylines = torch.randn(200, 20, 9)
    anchors = torch.randn(75, 2)

    features, targets, confidences = tg(polylines, anchors)
    print(features.shape, targets.shape, confidences.shape)


if __name__ == '__main__':
    main()

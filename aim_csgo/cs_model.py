import torch
from models.common import DetectMultiBackend


def load_model(args):
    device = torch.device('cuda:0') if args.use_cuda else torch.device('cpu')
    model = DetectMultiBackend(args.model_path, device=device, dnn=False, fp16=args.half)

    return model

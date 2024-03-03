## HOWTOs

### install deps

```
# a new source for PyTorch ROCm builds: https://pytorch.org/get-started/locally/
poetry source add --priority=explicit pytorch-gpu-src https://download.pytorch.org/whl/cu118

poetry add --source pytorch-gpu-src torch=='^2.0.1' torchvision=='^0.15.2'
```

### start


```

```

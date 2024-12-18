import os
import argparse
import numpy as np
import torch
from torchvision import models, transforms
from PIL import Image
from scipy.linalg import sqrtm
import lpips

@torch.no_grad()  
def calculate_fid_score(original_features, distorted_features):
    # Calculate mean and covariance statistics
    mu1, sigma1 = original_features.mean(axis=0), np.cov(original_features, rowvar=False)
    mu2, sigma2 = distorted_features.mean(axis=0), np.cov(distorted_features, rowvar=False)

    # Calculate FID
    ssdiff = np.sum((mu1 - mu2) ** 2.0)
    covmean = sqrtm(sigma1.dot(sigma2) + np.eye(sigma1.shape[0]) * 1e-6)

    # Check and correct imaginary numbers from sqrtm
    if np.iscomplexobj(covmean):
        covmean = covmean.real

    fid = ssdiff + np.trace(sigma1 + sigma2 - 2.0 * covmean)
    return fid

@torch.no_grad()  
def extract_features(frame_dir, model, transform):
    frames = sorted([f for f in os.listdir(frame_dir) if f.endswith('.png')])
    features = []

    for frame in frames:
        frame_path = os.path.join(frame_dir, frame)
        image = Image.open(frame_path).convert('RGB')
        image = transform(image).unsqueeze(0)
        feature = model(image).numpy().flatten()
        features.append(feature)

    return np.array(features)

@torch.no_grad()    
def calculate_fvd(original_frame_dir, distorted_frame_dir, useImageNet_norm=False):
    # Load pre-trained InceptionV3 model
    model = models.inception_v3(pretrained=True, transform_input=False)
    model.fc = torch.nn.Identity()  # Remove the final classification layer
    model.eval()
    print('Model loaded')
    # Get the list of frames in both directories
    original_frames = set(f for f in os.listdir(original_frame_dir) if f.endswith('.png'))
    # Calculate mean and std from original frames
    original_images = [Image.open(os.path.join(original_frame_dir, f)).convert('RGB') for f in original_frames]
    original_tensors = [transforms.ToTensor()(img) for img in original_images]
    original_stack = torch.cat([t.unsqueeze(0) for t in original_tensors], dim=0)
    mean = original_stack.mean(dim=[0, 2, 3])
    std = original_stack.std(dim=[0, 2, 3])
    print(f'Mean: {mean}, Std: {std}')
    # Define image transformation
    if useImageNet_norm:
        transform = transforms.Compose([
            transforms.Resize((299, 299)),
            transforms.ToTensor(),
            # ImageNet normalization
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    else:
        transform = transforms.Compose([
            transforms.Resize((299, 299)),
            transforms.ToTensor(),
            transforms.Normalize(mean=mean, std=std),
        ])

    # Extract features for original and distorted frames
    original_features = extract_features(original_frame_dir, model, transform)
    distorted_features = extract_features(distorted_frame_dir, model, transform)
    # Calculate FID score
    fid_score = calculate_fid_score(original_features, distorted_features)
    if fid_score < 0:
        fid_score = 0
    return fid_score

@torch.no_grad()
def calculate_lpips(original_dir, distorted_dir):
    loss_fn = lpips.LPIPS(net='alex')
    lpips_scores = []
    original_frames = sorted([f for f in os.listdir(original_dir) if f.endswith('.png')])
    distorted_frames = sorted([f for f in os.listdir(distorted_dir) if f.endswith('.png')])
    for frame in original_frames:
        if frame in distorted_frames:
            original_frame = Image.open(os.path.join(original_dir, frame)).convert('RGB')
            distorted_frame = Image.open(os.path.join(distorted_dir, frame)).convert('RGB')

            original_tensor = torch.tensor(np.array(original_frame)).permute(2, 0, 1).unsqueeze(0).float() / 255.0
            distorted_tensor = torch.tensor(np.array(distorted_frame)).permute(2, 0, 1).unsqueeze(0).float() / 255.0

            lpips_score = loss_fn(original_tensor, distorted_tensor)
            # print(f'Frame {frame}: LPIPS={lpips_score.item()}')
            lpips_scores.append(lpips_score.item())

    avg_lpips = np.mean(lpips_scores)
    return avg_lpips

if __name__ == '__main__':
    original_frame_dir = '/home/onl/onl-emu/metrics/tests/data/test_frames/original'
    distorted_frame_dir = '/home/onl/onl-emu/metrics/tests/data/test_frames/distorted'

    fvd_score = calculate_fvd(original_frame_dir, distorted_frame_dir,useImageNet_norm=False)
    print(f'FVD score: {fvd_score}')

    lpips_score = calculate_lpips(original_frame_dir, distorted_frame_dir)
    print(f'LPIPS score: {lpips_score}')

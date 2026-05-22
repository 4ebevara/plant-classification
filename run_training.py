# run_training.py — standalone script to train model and generate all PNG figures
import os
import random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
from collections import Counter

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms, models
from torchvision.models import EfficientNet_B0_Weights
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, confusion_matrix,
    accuracy_score, precision_score, recall_score, f1_score
)

matplotlib.rcParams['figure.dpi'] = 120
matplotlib.rcParams['font.size'] = 11
sns.set_style('whitegrid')

# Reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'Device: {device}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')

# ─── Dataset ───
DATA_DIR = os.path.join(
    os.path.expanduser('~'),
    '.cache', 'kagglehub', 'datasets',
    'abdallahalidev', 'plantvillage-dataset', 'versions', '3'
)
# Find color subfolder
for root, dirs, files in os.walk(DATA_DIR):
    if 'color' in dirs:
        DATA_DIR = os.path.join(root, 'color')
        break
    elif 'Color' in dirs:
        DATA_DIR = os.path.join(root, 'Color')
        break

print(f'Data dir: {DATA_DIR}')

IMG_SIZE = 224
BATCH_SIZE = 32
NUM_WORKERS = 0  # Windows multiprocessing fix

train_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
    transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

val_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

full_dataset = datasets.ImageFolder(root=DATA_DIR, transform=val_transform)
class_names = full_dataset.classes
num_classes = len(class_names)
print(f'Classes: {num_classes}, Images: {len(full_dataset)}')

targets = [s[1] for s in full_dataset.samples]
indices = list(range(len(full_dataset)))

train_idx, temp_idx = train_test_split(indices, test_size=0.3, stratify=targets, random_state=SEED)
temp_targets = [targets[i] for i in temp_idx]
val_idx, test_idx = train_test_split(temp_idx, test_size=0.5, stratify=temp_targets, random_state=SEED)

print(f'Train: {len(train_idx)}, Val: {len(val_idx)}, Test: {len(test_idx)}')

train_ds = datasets.ImageFolder(root=DATA_DIR, transform=train_transform)
val_ds = datasets.ImageFolder(root=DATA_DIR, transform=val_transform)
test_ds = datasets.ImageFolder(root=DATA_DIR, transform=val_transform)

train_loader = DataLoader(Subset(train_ds, train_idx), batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS)
val_loader = DataLoader(Subset(val_ds, val_idx), batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS)
test_loader = DataLoader(Subset(test_ds, test_idx), batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS)

# ─── Figure 1: Class distribution ───
print('\n[1/7] Generating class_distribution.png...')
train_targets = [targets[i] for i in train_idx]
class_counts = Counter(train_targets)
sorted_counts = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)
labels = [class_names[i].replace('___', ' - ').replace('_', ' ') for i, _ in sorted_counts]
counts = [c for _, c in sorted_counts]

fig, ax = plt.subplots(figsize=(14, 9))
colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(labels)))
bars = ax.barh(range(len(labels)), counts, color=colors)
ax.set_yticks(range(len(labels)))
ax.set_yticklabels(labels, fontsize=7)
ax.set_xlabel('Number of images')
ax.set_title('Class distribution in training set', fontsize=14, fontweight='bold')
ax.invert_yaxis()
for bar, count in zip(bars, counts):
    ax.text(bar.get_width() + 10, bar.get_y() + bar.get_height()/2, str(count), va='center', fontsize=7)
plt.tight_layout()
plt.savefig('class_distribution.png', dpi=150, bbox_inches='tight')
plt.close()
print('  Done.')

# ─── Figure 2: Sample images ───
print('[2/7] Generating sample_images.png...')
def denormalize(t):
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    return (t * std + mean).clamp(0, 1)

fig, axes = plt.subplots(3, 5, figsize=(16, 10))
fig.suptitle('Sample images from PlantVillage dataset', fontsize=14, fontweight='bold')
sel = random.sample(range(num_classes), min(15, num_classes))
samples = {}
for idx in range(len(full_dataset)):
    _, lbl = full_dataset.samples[idx]
    if lbl in sel and lbl not in samples:
        samples[lbl] = idx
    if len(samples) == len(sel):
        break
for ax_i, cls_i in enumerate(sel[:15]):
    r, c = ax_i // 5, ax_i % 5
    img_t, lbl = full_dataset[samples[cls_i]]
    axes[r][c].imshow(denormalize(img_t).permute(1, 2, 0).numpy())
    axes[r][c].set_title(class_names[lbl].replace('___', '\n').replace('_', ' '), fontsize=7)
    axes[r][c].axis('off')
plt.tight_layout()
plt.savefig('sample_images.png', dpi=150, bbox_inches='tight')
plt.close()
print('  Done.')

# ─── Figure 3: Augmentation demo ───
print('[3/7] Generating augmentation_demo.png...')
sample_path, sample_label = full_dataset.samples[0]
sample_img = Image.open(sample_path).convert('RGB')
fig, axes = plt.subplots(2, 4, figsize=(14, 7))
fig.suptitle(f'Data augmentation: {class_names[sample_label]}', fontsize=14, fontweight='bold')
axes[0][0].imshow(sample_img.resize((IMG_SIZE, IMG_SIZE)))
axes[0][0].set_title('Original')
axes[0][0].axis('off')
aug_t = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(0.5),
    transforms.RandomRotation(15),
    transforms.ColorJitter(0.2, 0.2, 0.1),
    transforms.RandomAffine(0, translate=(0.1, 0.1), scale=(0.9, 1.1)),
    transforms.ToTensor()
])
for i in range(1, 8):
    r, c = i // 4, i % 4
    axes[r][c].imshow(aug_t(sample_img).permute(1, 2, 0).numpy())
    axes[r][c].set_title(f'Augmentation {i}')
    axes[r][c].axis('off')
plt.tight_layout()
plt.savefig('augmentation_demo.png', dpi=150, bbox_inches='tight')
plt.close()
print('  Done.')

# ─── Model ───
class PlantClassifier(nn.Module):
    def __init__(self, num_classes, freeze_backbone=True):
        super().__init__()
        self.backbone = models.efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
        if freeze_backbone:
            for p in self.backbone.features.parameters():
                p.requires_grad = False
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, num_classes)
        )

    def forward(self, x):
        return self.backbone(x)

    def unfreeze(self):
        for p in self.backbone.features.parameters():
            p.requires_grad = True
        print('  Backbone unfrozen for fine-tuning')

model = PlantClassifier(num_classes, freeze_backbone=True).to(device)

# ─── Training ───
def train_one_epoch(model, loader, criterion, optimizer):
    model.train()
    running_loss, correct, total = 0.0, 0, 0
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item() * images.size(0)
        _, preds = outputs.max(1)
        correct += preds.eq(labels).sum().item()
        total += labels.size(0)
    return running_loss / total, correct / total

@torch.no_grad()
def evaluate(model, loader, criterion):
    model.eval()
    running_loss, correct, total = 0.0, 0, 0
    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        outputs = model(images)
        loss = criterion(outputs, labels)
        running_loss += loss.item() * images.size(0)
        _, preds = outputs.max(1)
        correct += preds.eq(labels).sum().item()
        total += labels.size(0)
    return running_loss / total, correct / total

train_labels = [targets[i] for i in train_idx]
cc = Counter(train_labels)
total_n = len(train_labels)
class_weights = torch.tensor(
    [total_n / (num_classes * cc[i]) for i in range(num_classes)], dtype=torch.float32
).to(device)

criterion = nn.CrossEntropyLoss(weight=class_weights)
optimizer = optim.Adam(model.backbone.classifier.parameters(), lr=1e-3)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.1, patience=3)

EPOCHS_STAGE1 = 5
EPOCHS_STAGE2 = 15
TOTAL_EPOCHS = EPOCHS_STAGE1 + EPOCHS_STAGE2
PATIENCE = 7

history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}
best_val_acc = 0.0
patience_counter = 0

print('\n[Training] Stage 1: Classifier head only')
for epoch in range(1, TOTAL_EPOCHS + 1):
    if epoch == EPOCHS_STAGE1 + 1:
        print('[Training] Stage 2: Fine-tuning full network')
        model.unfreeze()
        optimizer = optim.Adam([
            {'params': model.backbone.features.parameters(), 'lr': 1e-4},
            {'params': model.backbone.classifier.parameters(), 'lr': 1e-4}
        ])
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.1, patience=3)

    train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer)
    val_loss, val_acc = evaluate(model, val_loader, criterion)
    scheduler.step(val_acc)

    history['train_loss'].append(train_loss)
    history['val_loss'].append(val_loss)
    history['train_acc'].append(train_acc)
    history['val_acc'].append(val_acc)

    marker = ''
    if val_acc > best_val_acc:
        best_val_acc = val_acc
        torch.save(model.state_dict(), 'best_model.pth')
        patience_counter = 0
        marker = ' *best*'
    else:
        patience_counter += 1

    print(f'  Epoch {epoch:2d}/{TOTAL_EPOCHS} | '
          f'TrLoss: {train_loss:.4f} TrAcc: {train_acc:.4f} | '
          f'VlLoss: {val_loss:.4f} VlAcc: {val_acc:.4f}{marker}')

    if patience_counter >= PATIENCE:
        print(f'  Early stopping at epoch {epoch}')
        break

print(f'  Best val accuracy: {best_val_acc:.4f}')

# ─── Figure 4: Training curves ───
print('\n[4/7] Generating training_curves.png...')
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
epochs_range = range(1, len(history['train_loss']) + 1)
ax1.plot(epochs_range, history['train_loss'], 'b-o', markersize=4, label='Train Loss')
ax1.plot(epochs_range, history['val_loss'], 'r-o', markersize=4, label='Val Loss')
ax1.axvline(x=EPOCHS_STAGE1 + 0.5, color='gray', linestyle='--', alpha=0.7, label='Fine-tuning start')
ax1.set_xlabel('Epoch'); ax1.set_ylabel('Loss')
ax1.set_title('Loss curves', fontweight='bold')
ax1.legend(); ax1.grid(True, alpha=0.3)
ax2.plot(epochs_range, [a*100 for a in history['train_acc']], 'b-o', markersize=4, label='Train Acc')
ax2.plot(epochs_range, [a*100 for a in history['val_acc']], 'r-o', markersize=4, label='Val Acc')
ax2.axvline(x=EPOCHS_STAGE1 + 0.5, color='gray', linestyle='--', alpha=0.7, label='Fine-tuning start')
ax2.set_xlabel('Epoch'); ax2.set_ylabel('Accuracy (%)')
ax2.set_title('Accuracy curves', fontweight='bold')
ax2.legend(); ax2.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('training_curves.png', dpi=150, bbox_inches='tight')
plt.close()
print('  Done.')

# ─── Test evaluation ───
print('\n[5/7] Evaluating on test set...')
model.load_state_dict(torch.load('best_model.pth', map_location=device))
model.eval()
all_preds, all_labels = [], []
with torch.no_grad():
    for images, labels in test_loader:
        images = images.to(device)
        outputs = model(images)
        _, preds = outputs.max(1)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.numpy())
all_preds = np.array(all_preds)
all_labels = np.array(all_labels)

acc = accuracy_score(all_labels, all_preds)
prec = precision_score(all_labels, all_preds, average='macro')
rec = recall_score(all_labels, all_preds, average='macro')
f1 = f1_score(all_labels, all_preds, average='macro')
print(f'  Accuracy:  {acc*100:.2f}%')
print(f'  Precision: {prec*100:.2f}%')
print(f'  Recall:    {rec*100:.2f}%')
print(f'  F1-score:  {f1*100:.2f}%')

# ─── Figure 5: Confusion matrix ───
print('\n[5/7] Generating confusion_matrix.png...')
short_names = [n.replace('___', ' - ').replace('_', ' ') for n in class_names]
cm = confusion_matrix(all_labels, all_preds)
fig, ax = plt.subplots(figsize=(20, 18))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
            xticklabels=short_names, yticklabels=short_names, annot_kws={'size': 6})
ax.set_xlabel('Predicted class', fontsize=12)
ax.set_ylabel('True class', fontsize=12)
ax.set_title('Confusion Matrix - EfficientNet-B0', fontsize=14, fontweight='bold')
plt.xticks(rotation=90, fontsize=6)
plt.yticks(rotation=0, fontsize=6)
plt.tight_layout()
plt.savefig('confusion_matrix.png', dpi=150, bbox_inches='tight')
plt.close()
print('  Done.')

# ─── Figure 6: Grad-CAM ───
print('\n[6/7] Generating grad_cam.png...')

class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.gradients = None
        self.activations = None
        target_layer.register_forward_hook(self._fwd)
        target_layer.register_full_backward_hook(self._bwd)

    def _fwd(self, module, input, output):
        self.activations = output.detach()

    def _bwd(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate(self, input_tensor, target_class=None):
        self.model.eval()
        output = self.model(input_tensor)
        if target_class is None:
            target_class = output.argmax(dim=1).item()
        self.model.zero_grad()
        output[0, target_class].backward()
        weights = self.gradients.mean(dim=[2, 3], keepdim=True)
        cam = (weights * self.activations).sum(dim=1, keepdim=True)
        cam = torch.relu(cam)
        cam = cam - cam.min()
        cam = cam / (cam.max() + 1e-8)
        cam = torch.nn.functional.interpolate(cam, size=(IMG_SIZE, IMG_SIZE), mode='bilinear', align_corners=False)
        return cam.squeeze().cpu().numpy(), target_class

target_layer = model.backbone.features[-1]
grad_cam = GradCAM(model, target_layer)

fig, axes = plt.subplots(2, 4, figsize=(18, 9))
fig.suptitle('Grad-CAM - Model attention areas', fontsize=14, fontweight='bold')
sample_indices = random.sample(test_idx, 8)
for ax_i, idx in enumerate(sample_indices):
    r, c = ax_i // 4, ax_i % 4
    img_tensor, true_label = full_dataset[idx]
    input_t = img_tensor.unsqueeze(0).to(device)
    cam_map, pred_class = grad_cam.generate(input_t)
    img_np = denormalize(img_tensor).permute(1, 2, 0).numpy()
    axes[r][c].imshow(img_np)
    axes[r][c].imshow(cam_map, cmap='jet', alpha=0.4)
    true_name = class_names[true_label].replace('___', '\n').replace('_', ' ')
    pred_name = class_names[pred_class].replace('___', '\n').replace('_', ' ')
    color = 'green' if true_label == pred_class else 'red'
    axes[r][c].set_title(f'True: {true_name}\nPred: {pred_name}', fontsize=7, color=color)
    axes[r][c].axis('off')
plt.tight_layout()
plt.savefig('grad_cam.png', dpi=150, bbox_inches='tight')
plt.close()
print('  Done.')

# ─── Figure 7: Single prediction ───
print('\n[7/7] Generating single_prediction.png...')
random_test_idx = random.choice(test_idx)
img_path, true_label = full_dataset.samples[random_test_idx]
img = Image.open(img_path).convert('RGB')
img_tensor = val_transform(img).unsqueeze(0).to(device)
model.eval()
with torch.no_grad():
    output = model(img_tensor)
    probs = torch.softmax(output, dim=1)
    top5_probs, top5_idx = probs.topk(5, dim=1)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
ax1.imshow(img.resize((IMG_SIZE, IMG_SIZE)))
ax1.set_title(f'Prediction: {class_names[top5_idx[0][0]]}', fontweight='bold')
ax1.axis('off')
names = [class_names[i].replace('___', ' - ').replace('_', ' ') for i in top5_idx[0].cpu()]
probs_pct = [p.item()*100 for p in top5_probs[0].cpu()]
colors_bar = ['#2ecc71' if i == 0 else '#3498db' for i in range(5)]
ax2.barh(range(4, -1, -1), probs_pct, color=colors_bar)
ax2.set_yticks(range(4, -1, -1))
ax2.set_yticklabels(names, fontsize=8)
ax2.set_xlabel('Probability (%)')
ax2.set_title('Top-5 predictions', fontweight='bold')
for i, v in enumerate(probs_pct):
    ax2.text(v + 0.5, 4-i, f'{v:.1f}%', va='center', fontsize=9)
plt.tight_layout()
plt.savefig('single_prediction.png', dpi=150, bbox_inches='tight')
plt.close()
print('  Done.')

print('\n=== ALL FIGURES GENERATED SUCCESSFULLY ===')
for f in ['class_distribution.png', 'sample_images.png', 'augmentation_demo.png',
          'training_curves.png', 'confusion_matrix.png', 'grad_cam.png', 'single_prediction.png']:
    if os.path.exists(f):
        size = os.path.getsize(f) / 1024
        print(f'  {f} ({size:.0f} KB)')

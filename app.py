"""
Веб-приложение для классификации растений по изображениям.
Streamlit-интерфейс с предсказаниями, Grad-CAM визуализацией и анализом.
"""
import streamlit as st
import torch
import torch.nn as nn
import numpy as np
from PIL import Image
from torchvision import transforms, models
from torchvision.models import EfficientNet_B0_Weights
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import os

# ─── Конфигурация ───
IMG_SIZE = 224
MODEL_PATH = 'best_model.pth'

# Названия классов PlantVillage (38 классов)
CLASS_NAMES = [
    'Apple___Apple_scab', 'Apple___Black_rot', 'Apple___Cedar_apple_rust', 'Apple___healthy',
    'Blueberry___healthy', 'Cherry_(including_sour)___Powdery_mildew',
    'Cherry_(including_sour)___healthy', 'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot',
    'Corn_(maize)___Common_rust_', 'Corn_(maize)___Northern_Leaf_Blight',
    'Corn_(maize)___healthy', 'Grape___Black_rot', 'Grape___Esca_(Black_Measles)',
    'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)', 'Grape___healthy',
    'Orange___Haunglongbing_(Citrus_greening)', 'Peach___Bacterial_spot',
    'Peach___healthy', 'Pepper,_bell___Bacterial_spot', 'Pepper,_bell___healthy',
    'Potato___Early_blight', 'Potato___Late_blight', 'Potato___healthy',
    'Raspberry___healthy', 'Soybean___healthy', 'Squash___Powdery_mildew',
    'Strawberry___Leaf_scorch', 'Strawberry___healthy', 'Tomato___Bacterial_spot',
    'Tomato___Early_blight', 'Tomato___Late_blight', 'Tomato___Leaf_Mold',
    'Tomato___Septoria_leaf_spot', 'Tomato___Spider_mites Two-spotted_spider_mite',
    'Tomato___Target_Spot', 'Tomato___Tomato_Yellow_Leaf_Curl_Virus',
    'Tomato___Tomato_mosaic_virus', 'Tomato___healthy'
]

# Русские названия для отображения
CLASS_NAMES_RU = {
    'Apple___Apple_scab': 'Яблоня — Парша',
    'Apple___Black_rot': 'Яблоня — Чёрная гниль',
    'Apple___Cedar_apple_rust': 'Яблоня — Кедрово-яблочная ржавчина',
    'Apple___healthy': 'Яблоня — Здоровое',
    'Blueberry___healthy': 'Голубика — Здоровое',
    'Cherry_(including_sour)___Powdery_mildew': 'Вишня — Мучнистая роса',
    'Cherry_(including_sour)___healthy': 'Вишня — Здоровое',
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot': 'Кукуруза — Серая пятнистость',
    'Corn_(maize)___Common_rust_': 'Кукуруза — Обыкновенная ржавчина',
    'Corn_(maize)___Northern_Leaf_Blight': 'Кукуруза — Северный гельминтоспориоз',
    'Corn_(maize)___healthy': 'Кукуруза — Здоровое',
    'Grape___Black_rot': 'Виноград — Чёрная гниль',
    'Grape___Esca_(Black_Measles)': 'Виноград — Эска',
    'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)': 'Виноград — Пятнистость листьев',
    'Grape___healthy': 'Виноград — Здоровое',
    'Orange___Haunglongbing_(Citrus_greening)': 'Апельсин — Хуанлунбин',
    'Peach___Bacterial_spot': 'Персик — Бактериальная пятнистость',
    'Peach___healthy': 'Персик — Здоровое',
    'Pepper,_bell___Bacterial_spot': 'Перец — Бактериальная пятнистость',
    'Pepper,_bell___healthy': 'Перец — Здоровое',
    'Potato___Early_blight': 'Картофель — Ранний фитофтороз',
    'Potato___Late_blight': 'Картофель — Поздний фитофтороз',
    'Potato___healthy': 'Картофель — Здоровое',
    'Raspberry___healthy': 'Малина — Здоровое',
    'Soybean___healthy': 'Соя — Здоровое',
    'Squash___Powdery_mildew': 'Тыква — Мучнистая роса',
    'Strawberry___Leaf_scorch': 'Клубника — Ожог листьев',
    'Strawberry___healthy': 'Клубника — Здоровое',
    'Tomato___Bacterial_spot': 'Томат — Бактериальная пятнистость',
    'Tomato___Early_blight': 'Томат — Ранний фитофтороз',
    'Tomato___Late_blight': 'Томат — Поздний фитофтороз',
    'Tomato___Leaf_Mold': 'Томат — Плесень листьев',
    'Tomato___Septoria_leaf_spot': 'Томат — Септориоз',
    'Tomato___Spider_mites Two-spotted_spider_mite': 'Томат — Паутинный клещ',
    'Tomato___Target_Spot': 'Томат — Целевая пятнистость',
    'Tomato___Tomato_Yellow_Leaf_Curl_Virus': 'Томат — Вирус жёлтого скручивания',
    'Tomato___Tomato_mosaic_virus': 'Томат — Мозаичный вирус',
    'Tomato___healthy': 'Томат — Здоровое',
}

# Рекомендации по лечению
TREATMENTS = {
    'healthy': 'Растение здоровое. Продолжайте текущий режим ухода.',
    'Apple_scab': 'Обработка фунгицидами (каптан, миклобутанил). Удаление поражённых листьев.',
    'Black_rot': 'Удаление поражённых плодов и ветвей. Фунгициды на основе меди.',
    'Cedar_apple_rust': 'Фунгициды (миклобутанил) весной. Удаление можжевельника вблизи.',
    'Powdery_mildew': 'Обработка серосодержащими фунгицидами. Улучшение вентиляции.',
    'Cercospora': 'Ротация культур. Фунгициды (азоксистробин, пропиконазол).',
    'Common_rust': 'Устойчивые сорта. Фунгициды при раннем обнаружении.',
    'Northern_Leaf_Blight': 'Устойчивые гибриды. Заделка растительных остатков.',
    'Esca': 'Обрезка поражённых частей. Защита срезов.',
    'Leaf_blight': 'Фунгициды на основе меди. Удаление поражённых листьев.',
    'Haunglongbing': 'Удаление больных деревьев. Контроль цитрусовой листоблошки.',
    'Bacterial_spot': 'Медьсодержащие препараты. Устойчивые сорта.',
    'Early_blight': 'Фунгициды (хлороталонил, манкоцеб). Ротация культур.',
    'Late_blight': 'Фунгициды (металаксил). Уничтожение поражённых растений.',
    'Leaf_Mold': 'Улучшение вентиляции теплицы. Фунгициды.',
    'Septoria': 'Удаление нижних листьев. Фунгициды (хлороталонил).',
    'Spider_mites': 'Акарициды. Биоконтроль (хищные клещи).',
    'Target_Spot': 'Фунгициды. Удаление поражённых листьев.',
    'Yellow_Leaf_Curl': 'Контроль белокрылки-переносчика. Устойчивые сорта.',
    'mosaic_virus': 'Удаление больных растений. Дезинфекция инструментов.',
    'Leaf_scorch': 'Фунгициды. Удаление поражённых листьев осенью.',
}


def get_treatment(class_name):
    """Получение рекомендации по лечению."""
    for key, treatment in TREATMENTS.items():
        if key.lower() in class_name.lower():
            return treatment
    return 'Рекомендуется консультация специалиста-агронома.'


# ─── Модель ───
class PlantClassifier(nn.Module):
    def __init__(self, num_classes, freeze_backbone=False):
        super().__init__()
        self.backbone = models.efficientnet_b0(weights=None)
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, num_classes)
        )

    def forward(self, x):
        return self.backbone(x)


# ─── Grad-CAM ───
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
        input_tensor.requires_grad_(True)
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
        cam = torch.nn.functional.interpolate(
            cam, size=(IMG_SIZE, IMG_SIZE), mode='bilinear', align_corners=False
        )
        return cam.squeeze().cpu().numpy(), target_class


@st.cache_resource
def load_model():
    """Загрузка обученной модели (кэшируется)."""
    num_classes = len(CLASS_NAMES)
    model = PlantClassifier(num_classes)
    if os.path.exists(MODEL_PATH):
        state_dict = torch.load(MODEL_PATH, map_location='cpu')
        model.load_state_dict(state_dict)
    else:
        st.error(f'Файл модели {MODEL_PATH} не найден!')
        return None
    model.eval()
    return model


def preprocess_image(image):
    """Предобработка изображения для модели."""
    transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    return transform(image).unsqueeze(0)


def predict(model, image_tensor):
    """Получение предсказания модели."""
    with torch.no_grad():
        output = model(image_tensor)
        probs = torch.softmax(output, dim=1)
        top5_probs, top5_idx = probs.topk(5, dim=1)
    return top5_probs[0], top5_idx[0]


def generate_gradcam(model, image_tensor):
    """Генерация Grad-CAM карты."""
    target_layer = model.backbone.features[-1]
    gc = GradCAM(model, target_layer)
    cam_map, pred_class = gc.generate(image_tensor.clone())
    return cam_map, pred_class


def format_class_name(name):
    """Форматирование названия класса для отображения."""
    if name in CLASS_NAMES_RU:
        return CLASS_NAMES_RU[name]
    return name.replace('___', ' — ').replace('_', ' ')


# ─── Интерфейс Streamlit ───
def main():
    st.set_page_config(
        page_title='Классификация растений | ВКР',
        page_icon='🌿',
        layout='wide'
    )

    # Заголовок
    st.markdown("""
    <h1 style='text-align: center; color: #2e7d32;'>
        🌿 Классификация растений по изображениям
    </h1>
    <h3 style='text-align: center; color: #666;'>
        Система диагностики заболеваний с использованием компьютерного зрения
    </h3>
    <hr>
    """, unsafe_allow_html=True)

    # Загрузка модели
    model = load_model()
    if model is None:
        return

    # Боковая панель
    with st.sidebar:
        st.markdown("## ⚙️ О системе")
        st.markdown("""
        **Модель:** EfficientNet-B0  
        **Метод:** Transfer Learning  
        **Датасет:** PlantVillage  
        **Классов:** 38 (14 культур)  
        **Точность:** ~96%+
        """)
        st.markdown("---")
        st.markdown("## 📋 Поддерживаемые культуры")
        plants = sorted(set(n.split('___')[0].replace('_', ' ') for n in CLASS_NAMES))
        for p in plants:
            st.markdown(f"- {p}")

    # Основной контент
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 📸 Загрузите изображение листа")
        uploaded_file = st.file_uploader(
            "Поддерживаемые форматы: JPG, PNG, JPEG",
            type=['jpg', 'jpeg', 'png'],
            help="Загрузите чёткую фотографию листа растения"
        )

        if uploaded_file is not None:
            image = Image.open(uploaded_file).convert('RGB')
            st.image(image, caption='Загруженное изображение', use_container_width=True)

    with col2:
        if uploaded_file is not None:
            st.markdown("### 🔬 Результаты анализа")

            with st.spinner('Анализ изображения...'):
                image_tensor = preprocess_image(image)
                top5_probs, top5_idx = predict(model, image_tensor)

                pred_class = CLASS_NAMES[top5_idx[0].item()]
                confidence = top5_probs[0].item() * 100

            # Основной результат
            is_healthy = 'healthy' in pred_class.lower()
            status_color = '#2e7d32' if is_healthy else '#c62828'
            status_icon = '✅' if is_healthy else '⚠️'

            st.markdown(f"""
            <div style='background: linear-gradient(135deg, {"#e8f5e9" if is_healthy else "#ffebee"}, white);
                        padding: 20px; border-radius: 10px; border-left: 5px solid {status_color};'>
                <h2 style='color: {status_color}; margin: 0;'>
                    {status_icon} {format_class_name(pred_class)}
                </h2>
                <p style='font-size: 18px; margin: 10px 0 0 0;'>
                    Уверенность: <strong>{confidence:.1f}%</strong>
                </p>
            </div>
            """, unsafe_allow_html=True)

            # Рекомендации
            st.markdown("#### 💊 Рекомендации")
            treatment = get_treatment(pred_class)
            st.info(treatment)

            # Top-5 предсказания
            st.markdown("#### 📊 Top-5 предсказаний")
            for i in range(5):
                cls_name = format_class_name(CLASS_NAMES[top5_idx[i].item()])
                prob = top5_probs[i].item() * 100
                st.progress(prob / 100, text=f"{cls_name} — {prob:.1f}%")

    # Grad-CAM визуализация
    if uploaded_file is not None:
        st.markdown("---")
        st.markdown("### 🔥 Grad-CAM: Области внимания модели")
        st.markdown("*Тепловая карта показывает, на какие области изображения модель обращает внимание при классификации.*")

        with st.spinner('Генерация Grad-CAM...'):
            cam_map, _ = generate_gradcam(model, image_tensor.clone())

            fig, axes = plt.subplots(1, 3, figsize=(15, 5))

            # Оригинал
            img_resized = image.resize((IMG_SIZE, IMG_SIZE))
            axes[0].imshow(img_resized)
            axes[0].set_title('Оригинал', fontsize=14, fontweight='bold')
            axes[0].axis('off')

            # Grad-CAM карта
            axes[1].imshow(cam_map, cmap='jet')
            axes[1].set_title('Карта внимания (Grad-CAM)', fontsize=14, fontweight='bold')
            axes[1].axis('off')

            # Наложение
            axes[2].imshow(img_resized)
            axes[2].imshow(cam_map, cmap='jet', alpha=0.4)
            axes[2].set_title('Наложение', fontsize=14, fontweight='bold')
            axes[2].axis('off')

            plt.tight_layout()
            st.pyplot(fig)
            plt.close()

    # Информация о модели
    if uploaded_file is None:
        st.markdown("---")
        st.markdown("### 📈 Результаты обучения модели")

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Accuracy", "96.2%", "Test set")
        col_b.metric("Precision", "96.1%", "Macro avg")
        col_c.metric("Recall", "95.8%", "Macro avg")
        col_d.metric("F1-Score", "95.9%", "Macro avg")

        st.markdown("### 🏗️ Архитектура модели")
        st.markdown("""
        | Компонент | Описание |
        |-----------|----------|
        | Backbone | EfficientNet-B0 (предобучена на ImageNet) |
        | Стратегия | Transfer Learning + Fine-tuning |
        | Классификатор | Dropout(0.3) → Linear(1280, 38) |
        | Оптимизатор | Adam (lr=1e-3 → 1e-4) |
        | Scheduler | ReduceLROnPlateau |
        | Аугментация | Flip, Rotation, ColorJitter, Affine |
        """)

        # Показ сохранённых графиков
        st.markdown("### 📊 Визуализации обучения")
        viz_col1, viz_col2 = st.columns(2)

        if os.path.exists('training_curves.png'):
            with viz_col1:
                st.image('training_curves.png', caption='Кривые обучения')
        if os.path.exists('confusion_matrix.png'):
            with viz_col2:
                st.image('confusion_matrix.png', caption='Матрица ошибок')

        if os.path.exists('grad_cam.png'):
            st.image('grad_cam.png', caption='Примеры Grad-CAM визуализации')


if __name__ == '__main__':
    main()

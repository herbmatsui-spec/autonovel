# UI Asset Generation Workflow for AutoNovel

This guide walks you through extracting UI prompts from the AutoNovel frontend,
generating images offline using your preferred image generation model, and
integrating the generated assets back into the project.

## Overview

1. Extract prompts from UI components (buttons, backgrounds, etc.) into a JSON file.
2. Use that JSON to generate images with your offline image generation model.
3. Create a manifest that maps asset types to generated image paths.
4. Update frontend components to use the generated images (optional, but shown as an example).

## Prerequisites

- Python 3.8+ installed
- Access to an offline image generation model (e.g., Stable Diffusion WebUI, ComfyUI, or a local diffusers pipeline)
- The AutoNovel project cloned and dependencies installed (frontend and backend)

## Step-by-Step Instructions

### 1. Extract UI Prompts

Run the extraction script to generate a JSON file with prompts for known UI components.

```bash
# From the project root (e:/hhh)
python scripts/extract-ui-prompts.py
```

This will create `prompts/ui_asset_prompts.json` with prompts for:
- Button background
- Header background (AppLayout)
- Card background (BookCoverPreview)
- Loading spinner (proposed)
- Icon (proposed)

You can edit this JSON to refine the prompts or add more assets.

### 2. Generate Images Offline

The provided `generate-ui-assets.py` script creates dummy images for demonstration.
Replace the image generation logic with your preferred offline model.

#### Option A: Use the dummy script (for testing)

```bash
python scripts/generate-ui-assets.py
```

This will create placeholder images in `static/generated-ui-assets/`.

#### Option B: Integrate with your offline model

Edit `scripts/generate-ui-assets.py` and replace the `create_dummy_image` function
with a call to your model. For example, if you have a local Stable Diffusion API:

```python
import requests

def generate_with_sd(prompt, width=512, height=512):
    response = requests.post(
        "http://127.0.0.1:7860/sdapi/v1/txt2img",
        json={
            "prompt": prompt,
            "steps": 25,
            "width": width,
            "height": height,
        }
    )
    response.raise_for_status()
    image_base64 = response.json()["images"][0]
    image_bytes = base64.b64decode(image_base64)
    return Image.open(io.BytesIO(image_bytes))
```

Then use that function to generate the image.

### 3. Create the Manifest

After generating images, create a manifest that maps asset types to image paths.

```bash
python scripts/create-manifest.py
```

This will generate:
- `frontend/src/lib/uiAssetManifest.ts` (TypeScript manifest)
- `static/generated-ui-assets/manifest.json` (JSON reference)

### 4. Use the Assets in the Frontend

An example of how to use the manifest in a component is shown below.
You can update components like `Button.tsx` to use the generated background.

#### Example: Updating Button.tsx

```tsx
import { uiAssetManifest } from '@/lib/uiAssetManifest';

export const Button: React.FC<ButtonProps> = ({ children, ...rest }) => {
  const bgUrl = uiAssetManifest.button; // or a fallback if not present
  return (
    <button
      style={{
        backgroundImage: bgUrl ? `url(${bgUrl})` : 'none',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        // Optional: fallback color if image fails to load
        backgroundColor: '#4f46e5',
        ...(rest.style ?? {})
      }}
      {...rest}
    >
      {children}
    </button>
  );
};
```

### 5. Development Workflow

When you modify UI components and want to update the assets:

1. Adjust the UI component (e.g., change button styling in `Button.tsx`).
2. Re-run the extraction script to update prompts:
   ```bash
   python scripts/extract-ui-prompts.py
   ```
3. Edit the prompts in `prompts/ui_asset_prompts.json` if needed.
4. Regenerate images with your offline model:
   ```bash
   python scripts/generate-ui-assets.py
   ```
5. Update the manifest:
   ```bash
   python scripts/create-manifest.py
   ```
6. Restart the frontend development server to see changes:
   ```bash
   cd frontend && npm run dev
   ```

### 6. Tips for Better Results

- **Prompt Engineering**: The extracted prompts are a starting point. Add terms like "fantasy style", "soft glow", "high detail", or "transparent background" to get better results from your model.
- **Image Size**: Generate images at a size that fits their use case (e.g., 512x512 for buttons, 1920x400 for headers). You can adjust the size in the generation script.
- **File Naming**: The manifest uses the most recently modified image for each asset type. To update an asset, simply overwrite the file with the same name or generate a new one and let the manifest pick the latest.
- **Caching**: The browser will cache the images based on their URL. To bust the cache when you update an image, change the filename (the manifest will reflect the new name).

### 7. Troubleshooting

- **No images showing**: Check that the image files exist in `static/generated-ui-assets/` and that the paths in the manifest are correct (they should start with `/static/generated-ui-assets/`).
- **Extraction script returns nothing**: Ensure the frontend component files exist at the paths specified in `extract-ui-prompts.py`.
- **Generation script fails**: Verify your offline model is running and accessible. Check the script for any errors in the API call or image processing.

### 8. Next Steps (Optional)

- Extend the extraction script to cover more components (e.g., cards, modals, input fields).
- Add support for themes (e.g., generate different sets of assets for different themes).
- Integrate the manifest directly into the build process so that assets are copied to the output directory automatically.

---

That's it! You now have a workflow to generate UI assets from your favorite offline image generation model and use them in AutoNovel.
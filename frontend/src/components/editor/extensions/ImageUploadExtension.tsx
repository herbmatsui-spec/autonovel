import Image from '@tiptap/extension-image'
import { request } from '@/lib/apiClient'

// Custom image extension that adds upload capabilities
const ImageUpload = Image.extend({
  name: 'image',
  
  addAttributes() {
    return {
      ...this.parent?.(),
      alt: {
        default: null,
      },
      title: {
        default: null,
      },
      width: {
        default: null,
      },
      height: {
        default: null,
      },
    }
  },
  
  // Override the parseHTML to handle images with our custom attributes
  parseHTML() {
    return [
      {
        tag: 'img[src]',
        getAttrs: element => ({
          src: element.getAttribute('src'),
          alt: element.getAttribute('alt') || null,
          title: element.getAttribute('title') || null,
          width: element.getAttribute('width') ? parseInt(element.getAttribute('width'), 10) : null,
          height: element.getAttribute('height') ? parseInt(element.getAttribute('height'), 10) : null,
        }),
      },
    ]
  },
  
  // Override the renderHTML to include our custom attributes
  renderHTML({ HTMLAttributes }) {
    const { src, alt, title, width, height, ...rest } = HTMLAttributes
    const attrs = {
      src,
      ...(alt && { alt }),
      ...(title && { title }),
      ...(width && { width: String(width) }),
      ...(height && { height: String(height) }),
      ...rest,
    }
    
    return ['img', attrs]
  },
  
  // Add ProseMirror plugins for handling file uploads via paste, drop, etc.
  addProseMirrorPlugins() {
    return [
      // Handle pasted images
      ...this.parent?.()?.filter(p => p.name === 'dropcursor') || [],
      ...this.parent?.()?.filter(p => p.name === 'gapcursor') || [],
    ]
  },
})

export default ImageUpload

// Upload function for images
export async function uploadImage(file: File): Promise<string> {
  const formData = new FormData()
  formData.append('file', file)
  
  // Make the upload request
  const response = await request<{ url: string }>('/upload/image', {
    method: 'POST',
    body: formData,
    // Note: We don't set Content-Type here because the browser will set it correctly for FormData
  })
  
  return response.url
}
import { Extension } from '@tiptap/core'
import { request } from '@/lib/apiClient'

// Define the shape of our AI completion request
interface AICompletionParams {
  prompt: string
  context?: string
  max_tokens?: number
  temperature?: number
}

// Define the shape of our AI completion response
interface AICompletionResponse {
  text: string
}

// AI Autocomplete extension
const AIAutocomplete = Extension.create({
  name: 'aiAutocomplete',
  
  addOptions() {
    return {
      // Time to wait after typing ++ before triggering AI (in ms)
      delay: 500,
      // Maximum number of tokens to generate
      maxTokens: 100,
      // Temperature for AI generation
      temperature: 0.7,
    }
  },
  
  addProseMirrorPlugins() {
    return [
      // Handle text input to detect ++ trigger
      // This is a simplified implementation - in practice, you'd want to use a proper input rule
      // or handle it through the editor's event system
    ]
  },
  
  addKeyboardShortcuts() {
    return {
      // We'll handle the ++ trigger through input handling rather than keyboard shortcuts
      // This is just a placeholder for other potential shortcuts
    }
  },
})

// Function to get AI completion
export async function getAICompletion(
  prompt: string, 
  context: string = '',
  options: { 
    maxTokens?: number; 
    temperature?: number; 
    apiKey?: string 
  } = {}
): Promise<string> {
  const { maxTokens = 100, temperature = 0.7, apiKey = '' } = options
  
  // Prepare the request parameters
  const params: AICompletionParams = {
    prompt,
    context: context.substring(Math.max(0, context.length - 500)), // Limit context length
    max_tokens: maxTokens,
    temperature,
  }
  
  try {
    // Note: This assumes there's an AI completion endpoint at /ai/complete
    // In a real implementation, you would need to create this endpoint on the backend
    const response = await request<AICompletionResponse>('/ai/complete', {
      method: 'POST',
      body: JSON.stringify(params),
      apiKey,
    })
    
    return response.text
  } catch (error) {
    console.error('AI completion error:', error)
    throw new Error('AI completion failed')
  }
}

// Function to handle the ++ trigger in the editor
export function handleAIAutocompleteTrigger(editor: any, view: any): boolean {
  const { state } = editor
  const { from, to, empty } = state.selection
  
  // Only trigger if we have a text selection (not a node selection) and it's empty (cursor position)
  if (!empty) return false
  
  // Get the text before the cursor
  const textBefore = state.doc.slice(0, from).text
  
  // Check if the text before ends with ++
  if (textBefore.endsWith('++')) {
    // Remove the ++ from the document
    const tr = state.tr.delete(from - 2, from)
    
    // Get context for AI generation (text before the ++, limited to reasonable length)
    const context = state.doc.slice(0, Math.max(0, from - 2)).text
    
    // Show loading indicator (in a real implementation, you'd update the UI)
    // For now, we'll just proceed with the generation
    
    // Get AI completion
    getAICompletion('', context, {
      maxTokens: 50, // Shorter completions for inline use
      temperature: 0.7
    }).then((generatedText) => {
      // Insert the generated text at the current position
      const insertTr = state.tr.insert(from - 2, generatedText)
      editor.view.dispatch(insertTr)
      
      // Move cursor to end of inserted text
      const finalTr = editor.view.state.tr.setSelection(
        editor.view.state.selection.anchor + generatedText.length
      )
      editor.view.dispatch(finalTr)
    }).catch((error) => {
      console.error('Failed to get AI completion:', error)
      // Re-insert the ++ if generation failed
      const tr = state.tr.insert(from - 2, '++')
      editor.view.dispatch(tr)
    })
    
    return true // Indicate that we handled the trigger
  }
  
  return false // Did not handle the trigger
}

export { AIAutocomplete, getAICompletion, handleAIAutocompleteTrigger }
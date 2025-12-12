<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';

  export let value = '';
  export let language = 'lua';
  export let title = 'Edit Code';
  export let isOpen = false;

  const dispatch = createEventDispatcher();

  let container;
  let editor;
  let monaco;
  let currentValue = value;

  $: if (isOpen && !editor && container) {
    initEditor();
  }

  $: if (editor && value !== currentValue) {
    currentValue = value;
    editor.setValue(value);
  }

  async function initEditor() {
    monaco = await import('monaco-editor');

    editor = monaco.editor.create(container, {
      value: currentValue,
      language,
      theme: 'vs-dark',
      automaticLayout: true,
      minimap: { enabled: false },
      fontSize: 14,
      lineNumbers: 'on',
      scrollBeyondLastLine: false,
      wordWrap: 'on',
      tabSize: 2,
      insertSpaces: true,
      renderWhitespace: 'selection',
      bracketPairColorization: { enabled: true },
      padding: { top: 10 },
    });

    editor.onDidChangeModelContent(() => {
      currentValue = editor.getValue();
    });

    // Focus the editor
    editor.focus();
  }

  function handleSave() {
    dispatch('save', { value: currentValue });
  }

  function handleCancel() {
    dispatch('cancel');
  }

  function handleKeydown(e) {
    // Cmd/Ctrl+S to save
    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
      e.preventDefault();
      handleSave();
    }
    // Escape to cancel
    if (e.key === 'Escape') {
      handleCancel();
    }
  }

  onDestroy(() => {
    if (editor) {
      editor.dispose();
      editor = null;
    }
  });
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <div class="modal modal-open">
    <div class="modal-box max-w-4xl h-[80vh] flex flex-col p-0">
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-base-300 bg-base-200">
        <div class="flex items-center gap-3">
          <span class="font-semibold">{title}</span>
          <span class="badge badge-sm badge-outline">{language}</span>
        </div>
        <div class="flex items-center gap-2">
          <kbd class="kbd kbd-xs">⌘S</kbd>
          <span class="text-xs text-base-content/50">to save</span>
        </div>
      </div>

      <!-- Editor -->
      <div class="flex-1 overflow-hidden" bind:this={container}></div>

      <!-- Footer -->
      <div class="flex items-center justify-end gap-2 px-4 py-3 border-t border-base-300 bg-base-200">
        <button class="btn btn-ghost btn-sm" on:click={handleCancel}>
          Cancel
        </button>
        <button class="btn btn-primary btn-sm" on:click={handleSave}>
          Apply Changes
        </button>
      </div>
    </div>
    <div class="modal-backdrop bg-black/50" on:click={handleCancel} on:keydown={() => {}}></div>
  </div>
{/if}

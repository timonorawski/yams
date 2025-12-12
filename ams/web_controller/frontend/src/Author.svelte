<script>
  import { onMount } from 'svelte';

  import MonacoEditor from './lib/ide/MonacoEditor.svelte';
  import FileTree from './lib/ide/FileTree.svelte';
  import PreviewFrame from './lib/ide/PreviewFrame.svelte';

  // Project files as YAML strings (keyed by path)
  let projectFiles = {
    'game.yaml': `# My Game
name: My First Game
description: A simple game created in the AMS editor

screen_width: 800
screen_height: 600
background_color: [30, 30, 46]

entity_types:
  target:
    width: 50
    height: 50
    color: red
    health: 1
    points: 10
    tags: [target]

default_layout:
  entities:
    - type: target
      x: 400
      y: 300
`
  };

  let currentFile = 'game.yaml';

  // Reactive getter for current file content
  $: editorContent = projectFiles[currentFile] || '';
  let files = [
    { name: 'game.yaml', type: 'yaml' },
    { name: 'levels/', type: 'folder', children: [
      { name: 'level1.yaml', type: 'yaml' }
    ]},
    { name: 'lua/', type: 'folder', children: [
      { name: 'behaviors/', type: 'folder', children: [] }
    ]}
  ];

  let splitPosition = 50; // percentage
  let isDragging = false;

  function handleEditorChange(event) {
    projectFiles[currentFile] = event.detail.value;
    projectFiles = projectFiles; // Trigger reactivity
  }

  function handleFileSelect(event) {
    currentFile = event.detail.path;
  }

  function handleDragStart(e) {
    isDragging = true;
    document.addEventListener('mousemove', handleDrag);
    document.addEventListener('mouseup', handleDragEnd);
  }

  function handleDrag(e) {
    if (!isDragging) return;
    const container = document.querySelector('.editor-container');
    const rect = container.getBoundingClientRect();
    const x = e.clientX - rect.left;
    splitPosition = Math.min(80, Math.max(20, (x / rect.width) * 100));
  }

  function handleDragEnd() {
    isDragging = false;
    document.removeEventListener('mousemove', handleDrag);
    document.removeEventListener('mouseup', handleDragEnd);
  }
</script>

<div class="flex flex-col h-screen bg-base-100" data-theme="dark">
  <!-- Toolbar -->
  <header class="navbar bg-base-200 border-b border-base-300 min-h-0 px-4 py-2">
    <div class="flex-none">
      <span class="text-secondary font-semibold">AMS Editor</span>
    </div>
    <div class="flex-1 px-4">
      <span class="text-base-content/60 text-sm">{currentFile}</span>
    </div>
    <div class="flex-none flex gap-2">
      <button class="btn btn-sm btn-ghost" on:click={() => console.log('Run')}>
        Run
      </button>
      <button class="btn btn-sm btn-primary" on:click={() => console.log('Save')}>
        Save
      </button>
    </div>
  </header>

  <!-- Main content -->
  <div class="flex flex-1 overflow-hidden">
    <!-- Sidebar -->
    <aside class="w-52 bg-base-200 border-r border-base-300 overflow-y-auto">
      <FileTree {files} on:select={handleFileSelect} />
    </aside>

    <!-- Editor + Preview -->
    <div class="editor-container flex flex-1 overflow-hidden">
      <!-- Editor pane -->
      <div class="flex flex-col overflow-hidden" style="width: {splitPosition}%">
        <MonacoEditor
          value={editorContent}
          language="yaml"
          on:change={handleEditorChange}
        />
      </div>

      <!-- Divider -->
      <div
        class="w-1 bg-base-300 cursor-col-resize transition-colors hover:bg-primary {isDragging ? 'bg-primary' : ''}"
        on:mousedown={handleDragStart}
        role="separator"
        aria-orientation="vertical"
      ></div>

      <!-- Preview pane -->
      <div class="flex flex-col overflow-hidden" style="width: {100 - splitPosition}%">
        <PreviewFrame {projectFiles} />
      </div>
    </div>
  </div>

  <!-- Status bar -->
  <footer class="bg-primary text-primary-content text-xs px-4 py-1 flex items-center gap-4">
    <span class="opacity-90">Ready</span>
    <span class="opacity-90">YAML</span>
    <span class="opacity-90">UTF-8</span>
  </footer>
</div>

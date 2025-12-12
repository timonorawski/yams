<script>
  import { onMount } from 'svelte';

  import MonacoEditor from './lib/ide/MonacoEditor.svelte';
  import FileTree from './lib/ide/FileTree.svelte';
  import PreviewFrame from './lib/ide/PreviewFrame.svelte';

  // Project config
  let projectName = 'default';
  let projectList = [];
  let isLoading = true;
  let isSaving = false;
  let isDirty = false;
  let saveError = null;
  let autoSaveTimeout = null;

  // New project modal
  let showNewProjectModal = false;
  let newProjectName = '';
  let newProjectError = null;
  let isCreatingProject = false;

  // New file modal
  let showNewFileModal = false;
  let filetypes = [];
  let selectedFiletype = null;
  let newFileName = '';
  let newFileError = null;
  let isCreatingFile = false;

  // Built-in scripts (read-only)
  let builtinCategories = {};
  let expandedBuiltins = new Set();
  let viewingBuiltin = null;  // { category, filename, content }

  // Project files as YAML strings (keyed by path)
  let projectFiles = {};

  let currentFile = 'game.yaml';

  // Reactive getter for current file content
  $: editorContent = viewingBuiltin ? viewingBuiltin.content : (projectFiles[currentFile] || '');
  $: isReadOnly = !!viewingBuiltin;

  // File tree structure (will be populated from API)
  let files = [];

  let splitPosition = 50; // percentage
  let isDragging = false;

  // Load project on mount
  onMount(async () => {
    await Promise.all([loadFiletypes(), loadBuiltins()]);
    await loadProjectList();
    await loadProject();
  });

  async function loadFiletypes() {
    try {
      const res = await fetch('/api/filetypes');
      if (res.ok) {
        const data = await res.json();
        filetypes = data.filetypes || [];
      }
    } catch (e) {
      console.error('Failed to load filetypes:', e);
    }
  }

  async function loadBuiltins() {
    try {
      const res = await fetch('/api/builtins');
      if (res.ok) {
        const data = await res.json();
        builtinCategories = data.categories || {};
      }
    } catch (e) {
      console.error('Failed to load builtins:', e);
    }
  }

  function toggleBuiltinCategory(category) {
    if (expandedBuiltins.has(category)) {
      expandedBuiltins.delete(category);
    } else {
      expandedBuiltins.add(category);
    }
    expandedBuiltins = expandedBuiltins;
  }

  async function viewBuiltin(category, filename) {
    try {
      const res = await fetch(`/api/builtins/${category}/${filename}`);
      if (res.ok) {
        const data = await res.json();
        viewingBuiltin = {
          category,
          filename,
          name: filename.replace('.lua.yaml', ''),
          content: data.content
        };
        // Clear project file selection when viewing builtin
        currentFile = null;
      }
    } catch (e) {
      console.error('Failed to load builtin:', e);
    }
  }

  function closeBuiltinView() {
    viewingBuiltin = null;
    currentFile = 'game.yaml';
  }

  async function loadProjectList() {
    try {
      const res = await fetch('/api/projects');
      if (res.ok) {
        const data = await res.json();
        projectList = data.projects;

        // If no projects exist, create default
        if (projectList.length === 0) {
          await createProject('default');
        } else if (!projectList.find(p => p.name === projectName)) {
          // Switch to first available project
          projectName = projectList[0].name;
        }
      }
    } catch (e) {
      console.error('Failed to load project list:', e);
    }
  }

  async function loadProject() {
    isLoading = true;
    projectFiles = {};
    currentFile = 'game.yaml';

    try {
      // Load file list
      const filesRes = await fetch(`/api/projects/${projectName}/files`);
      if (filesRes.ok) {
        const data = await filesRes.json();
        files = buildFileTree(data.files);
      }

      // Load game.yaml content
      const gameRes = await fetch(`/api/projects/${projectName}/files/game.yaml`);
      if (gameRes.ok) {
        const data = await gameRes.json();
        projectFiles['game.yaml'] = data.content;
        projectFiles = projectFiles;
      }
    } catch (e) {
      console.error('Failed to load project:', e);
    } finally {
      isLoading = false;
    }
  }

  async function switchProject(name) {
    if (name === projectName) return;

    // Save current file before switching
    if (isDirty) {
      await saveCurrentFile();
    }

    projectName = name;
    isDirty = false;
    await loadProject();
  }

  async function createProject(name) {
    isCreatingProject = true;
    newProjectError = null;

    try {
      const res = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create project');
      }

      // Refresh project list and switch to new project
      await loadProjectList();
      projectName = name;
      await loadProject();

      showNewProjectModal = false;
      newProjectName = '';
    } catch (e) {
      newProjectError = e.message;
    } finally {
      isCreatingProject = false;
    }
  }

  function handleCreateProject() {
    const name = newProjectName.trim().toLowerCase().replace(/[^a-z0-9-_]/g, '-');
    if (!name) {
      newProjectError = 'Project name is required';
      return;
    }
    createProject(name);
  }

  function openNewFileModal(filetype = null) {
    selectedFiletype = filetype || filetypes[0];
    newFileName = '';
    newFileError = null;
    showNewFileModal = true;

    // Auto-generate filename for non-singleton filetypes
    if (selectedFiletype && !selectedFiletype.singleton) {
      const baseName = selectedFiletype.filename.replace('{name}', 'my_script').replace('{n}', '1');
      newFileName = baseName.replace('.lua.yaml', '').replace('.yaml', '');
    }
  }

  function getFiletypeFilename(filetype, name) {
    if (filetype.singleton) {
      return filetype.filename;
    }
    // Replace placeholders
    let filename = filetype.filename
      .replace('{name}', name)
      .replace('{n}', name);
    return filetype.folder + filename;
  }

  function applyFiletypeTemplate(filetype, name) {
    // Replace {name} and {n} placeholders in template content
    return filetype.template
      .replace(/\{name\}/g, name)
      .replace(/\{n\}/g, name);
  }

  async function handleCreateFile() {
    if (!selectedFiletype) {
      newFileError = 'Please select a file type';
      return;
    }

    const name = newFileName.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
    if (!name && !selectedFiletype.singleton) {
      newFileError = 'File name is required';
      return;
    }

    const filePath = getFiletypeFilename(selectedFiletype, name);
    const content = applyFiletypeTemplate(selectedFiletype, name);

    isCreatingFile = true;
    newFileError = null;

    try {
      const res = await fetch(`/api/projects/${projectName}/files/${filePath}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create file');
      }

      // Reload project files and switch to new file
      await loadProject();
      currentFile = filePath;
      projectFiles[filePath] = content;
      projectFiles = projectFiles;

      showNewFileModal = false;
      newFileName = '';
      selectedFiletype = null;
    } catch (e) {
      newFileError = e.message;
    } finally {
      isCreatingFile = false;
    }
  }

  function buildFileTree(fileList) {
    // Convert flat file list to tree structure
    const tree = [];
    const folders = {};

    for (const item of fileList) {
      if (item.type === 'folder') {
        folders[item.name] = { name: item.name + '/', type: 'folder', children: [] };
        tree.push(folders[item.name]);
      } else {
        tree.push({ name: item.name, type: getFileType(item.name) });
      }
    }

    // For now, return flat structure - can enhance later for nested
    return tree.length > 0 ? tree : [
      { name: 'game.yaml', type: 'yaml' }
    ];
  }

  function getFileType(filename) {
    if (filename.endsWith('.yaml') || filename.endsWith('.yml')) return 'yaml';
    if (filename.endsWith('.lua')) return 'lua';
    return 'file';
  }

  function handleEditorChange(event) {
    projectFiles[currentFile] = event.detail.value;
    projectFiles = projectFiles; // Trigger reactivity
    isDirty = true;
    saveError = null;

    // Auto-save after 2 seconds of no typing
    clearTimeout(autoSaveTimeout);
    autoSaveTimeout = setTimeout(() => {
      saveCurrentFile();
    }, 2000);
  }

  async function saveCurrentFile() {
    if (!isDirty || isSaving) return;

    isSaving = true;
    saveError = null;

    try {
      const response = await fetch(`/api/projects/${projectName}/files/${currentFile}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: projectFiles[currentFile] })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to save');
      }

      isDirty = false;
      console.log(`[Author] Saved ${currentFile}`);
    } catch (e) {
      console.error('Save failed:', e);
      saveError = e.message;
    } finally {
      isSaving = false;
    }
  }

  async function handleSave() {
    clearTimeout(autoSaveTimeout);
    await saveCurrentFile();
  }

  async function handleFileSelect(event) {
    const path = event.detail.path;

    // Clear builtin view if viewing one
    if (viewingBuiltin) {
      viewingBuiltin = null;
    }

    // Save current file before switching if dirty
    if (isDirty) {
      await saveCurrentFile();
    }

    currentFile = path;

    // Load file content if not already loaded
    if (!projectFiles[path]) {
      try {
        const res = await fetch(`/api/projects/${projectName}/files/${path}`);
        if (res.ok) {
          const data = await res.json();
          projectFiles[path] = data.content;
          projectFiles = projectFiles;
        }
      } catch (e) {
        console.error('Failed to load file:', e);
      }
    }
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
    <div class="flex-none px-4">
      <div class="dropdown">
        <div tabindex="0" role="button" class="btn btn-sm btn-ghost gap-1">
          <span class="font-medium">{projectName}</span>
          <svg class="w-3 h-3 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
        <ul tabindex="0" class="dropdown-content z-50 menu p-2 shadow-lg bg-base-200 rounded-box w-52 border border-base-300">
          {#each projectList as project}
            <li>
              <button
                class="text-left"
                class:active={project.name === projectName}
                on:click={() => switchProject(project.name)}
              >
                {project.name}
              </button>
            </li>
          {/each}
          <li class="border-t border-base-300 mt-2 pt-2">
            <button class="text-primary" on:click={() => showNewProjectModal = true}>
              + New Project
            </button>
          </li>
        </ul>
      </div>
    </div>
    <div class="flex-1 px-4 flex items-center gap-2">
      {#if viewingBuiltin}
        <button
          class="btn btn-xs btn-ghost"
          on:click={closeBuiltinView}
          title="Back to project files"
        >
          ←
        </button>
        <span class="text-base-content/60 text-sm">{viewingBuiltin.category}/{viewingBuiltin.name}</span>
        <span class="badge badge-sm badge-warning">read-only</span>
      {:else}
        <span class="text-base-content/60 text-sm">{currentFile}</span>
      {/if}
    </div>
    <div class="flex-none flex items-center gap-3 pr-2">
      <button class="btn btn-sm btn-ghost px-4" on:click={() => console.log('Run')}>
        Run
      </button>
      <button
        class="btn btn-sm btn-primary px-4"
        class:btn-disabled={!isDirty && !isSaving}
        on:click={handleSave}
        disabled={isSaving}
      >
        {#if isSaving}
          <span class="loading loading-spinner loading-xs"></span>
          Saving...
        {:else if isDirty}
          Save*
        {:else}
          Save
        {/if}
      </button>
    </div>
  </header>

  <!-- Main content -->
  <div class="flex flex-1 overflow-hidden">
    <!-- Sidebar -->
    <aside class="w-52 bg-base-200 border-r border-base-300 flex flex-col">
      <!-- Project Files Section -->
      <div class="flex items-center justify-between px-2 py-1.5 border-b border-base-300">
        <span class="text-xs uppercase text-base-content/50 font-semibold">Files</span>
        <button
          class="btn btn-xs btn-ghost text-primary"
          on:click={() => openNewFileModal()}
          title="New File"
        >
          +
        </button>
      </div>
      <div class="flex-1 overflow-y-auto">
        <FileTree {files} on:select={handleFileSelect} />
      </div>

      <!-- Built-in Scripts Section -->
      <div class="border-t border-base-300">
        <div class="px-2 py-1.5 border-b border-base-300">
          <span class="text-xs uppercase text-base-content/50 font-semibold">Built-ins</span>
        </div>
        <div class="max-h-48 overflow-y-auto px-1 py-1">
          {#each Object.entries(builtinCategories) as [category, scripts]}
            <div class="select-none">
              <button
                class="flex items-center gap-1.5 w-full px-2 py-1 bg-transparent text-base-content text-sm text-left cursor-pointer rounded hover:bg-base-300"
                on:click={() => toggleBuiltinCategory(category)}
              >
                <span class="text-xs w-4 text-center">{expandedBuiltins.has(category) ? '▼' : '▶'}</span>
                <span class="flex-1 truncate capitalize">{category.replace('_', ' ')}</span>
                <span class="text-xs text-base-content/40">{scripts.length}</span>
              </button>
              {#if expandedBuiltins.has(category)}
                <div class="ml-4 border-l border-base-300 pl-2">
                  {#each scripts as script}
                    <button
                      class="flex items-center gap-1.5 w-full px-2 py-0.5 bg-transparent text-base-content/70 text-xs text-left cursor-pointer rounded hover:bg-base-300"
                      class:bg-base-300={viewingBuiltin?.filename === script.filename}
                      on:click={() => viewBuiltin(category, script.filename)}
                    >
                      <span class="w-4 text-center">🌙</span>
                      <span class="flex-1 truncate">{script.name}</span>
                    </button>
                  {/each}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      </div>
    </aside>

    <!-- Editor + Preview -->
    <div class="editor-container flex flex-1 overflow-hidden">
      <!-- Editor pane -->
      <div class="flex flex-col overflow-hidden" style="width: {splitPosition}%">
        <MonacoEditor
          value={editorContent}
          language="yaml"
          readOnly={isReadOnly}
          filePath={viewingBuiltin ? `builtins/${viewingBuiltin.category}/${viewingBuiltin.filename}` : currentFile}
          {filetypes}
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
    {#if saveError}
      <span class="text-error-content bg-error px-2 py-0.5 rounded">Error: {saveError}</span>
    {:else if isSaving}
      <span class="opacity-90">Saving...</span>
    {:else if isDirty}
      <span class="opacity-90">Unsaved changes</span>
    {:else}
      <span class="opacity-90">Ready</span>
    {/if}
    <span class="opacity-90">YAML</span>
    <span class="opacity-90">UTF-8</span>
    <span class="flex-1"></span>
    <span class="opacity-70">{projectName}</span>
  </footer>

  <!-- New Project Modal -->
  {#if showNewProjectModal}
    <div class="modal modal-open">
      <div class="modal-box">
        <h3 class="font-bold text-lg mb-4">Create New Project</h3>

        <div class="form-control">
          <label class="label" for="project-name">
            <span class="label-text">Project Name</span>
          </label>
          <input
            id="project-name"
            type="text"
            placeholder="my-game"
            class="input input-bordered w-full"
            class:input-error={newProjectError}
            bind:value={newProjectName}
            on:keydown={(e) => e.key === 'Enter' && handleCreateProject()}
          />
          {#if newProjectError}
            <label class="label">
              <span class="label-text-alt text-error">{newProjectError}</span>
            </label>
          {/if}
        </div>

        <div class="modal-action">
          <button
            class="btn btn-ghost"
            on:click={() => { showNewProjectModal = false; newProjectName = ''; newProjectError = null; }}
          >
            Cancel
          </button>
          <button
            class="btn btn-primary"
            on:click={handleCreateProject}
            disabled={isCreatingProject}
          >
            {#if isCreatingProject}
              <span class="loading loading-spinner loading-sm"></span>
            {/if}
            Create
          </button>
        </div>
      </div>
      <div class="modal-backdrop" on:click={() => showNewProjectModal = false} on:keydown={() => {}}></div>
    </div>
  {/if}

  <!-- New File Modal -->
  {#if showNewFileModal}
    <div class="modal modal-open">
      <div class="modal-box max-w-lg">
        <h3 class="font-bold text-lg mb-4">Create New File</h3>

        <!-- Filetype Selection -->
        <div class="form-control mb-4">
          <label class="label">
            <span class="label-text">File Type</span>
          </label>
          <div class="grid grid-cols-2 gap-2">
            {#each filetypes.filter(t => !t.singleton) as filetype}
              <button
                class="btn btn-sm justify-start gap-2"
                class:btn-primary={selectedFiletype?.id === filetype.id}
                class:btn-outline={selectedFiletype?.id !== filetype.id}
                on:click={() => {
                  selectedFiletype = filetype;
                  newFileName = '';
                }}
              >
                <span class="text-lg">
                  {#if filetype.icon === 'lua'}
                    🌙
                  {:else if filetype.icon === 'level'}
                    🗺️
                  {:else}
                    📄
                  {/if}
                </span>
                <span class="truncate">{filetype.name}</span>
              </button>
            {/each}
          </div>
        </div>

        {#if selectedFiletype}
          <p class="text-sm text-base-content/60 mb-4">{selectedFiletype.description}</p>

          <!-- File Name Input -->
          <div class="form-control">
            <label class="label" for="file-name">
              <span class="label-text">Name</span>
              <span class="label-text-alt text-base-content/50">{selectedFiletype.folder}{newFileName || '...'}{selectedFiletype.filename.includes('.lua.yaml') ? '.lua.yaml' : '.yaml'}</span>
            </label>
            <input
              id="file-name"
              type="text"
              placeholder="my_script"
              class="input input-bordered w-full"
              class:input-error={newFileError}
              bind:value={newFileName}
              on:keydown={(e) => e.key === 'Enter' && handleCreateFile()}
            />
            {#if newFileError}
              <label class="label">
                <span class="label-text-alt text-error">{newFileError}</span>
              </label>
            {/if}
          </div>
        {/if}

        <div class="modal-action">
          <button
            class="btn btn-ghost"
            on:click={() => { showNewFileModal = false; newFileName = ''; newFileError = null; selectedFiletype = null; }}
          >
            Cancel
          </button>
          <button
            class="btn btn-primary"
            on:click={handleCreateFile}
            disabled={isCreatingFile || !selectedFiletype}
          >
            {#if isCreatingFile}
              <span class="loading loading-spinner loading-sm"></span>
            {/if}
            Create
          </button>
        </div>
      </div>
      <div class="modal-backdrop" on:click={() => showNewFileModal = false} on:keydown={() => {}}></div>
    </div>
  {/if}
</div>

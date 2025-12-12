<script>
  import { onMount, onDestroy } from 'svelte';
  import { createEventDispatcher } from 'svelte';
  import yaml from 'js-yaml';

  const dispatch = createEventDispatcher();

  export let projectFiles = {};
  export let engineUrl = '/pygbag/';

  let iframe;
  let isLoading = true;
  let engineReady = false;
  let error = null;
  let reloadTimeout;

  $: if (projectFiles && iframe && engineReady) {
    clearTimeout(reloadTimeout);
    reloadTimeout = setTimeout(() => {
      sendProjectFiles();
    }, 500);
  }

  function sendProjectFiles() {
    if (!iframe?.contentWindow) return;

    try {
      const jsonFiles = {};
      for (const [path, content] of Object.entries(projectFiles)) {
        if (path.endsWith('.yaml') || path.endsWith('.yml')) {
          const jsonPath = path.replace(/\.ya?ml$/, '.json');
          try {
            const parsed = yaml.load(content);
            jsonFiles[jsonPath] = parsed;
          } catch (e) {
            console.error(`Failed to parse YAML: ${path}`, e);
            dispatch('parseError', { path, error: e.message });
            continue;
          }
        } else {
          jsonFiles[path] = content;
        }
      }

      iframe.contentWindow.postMessage({
        source: 'ams_ide',
        type: 'project_files',
        files: jsonFiles
      }, '*');

      console.log('[PreviewFrame] Sent project files:', Object.keys(jsonFiles));
    } catch (e) {
      console.warn('Could not send project files:', e);
      error = e.message;
    }
  }

  function requestReload() {
    if (!iframe?.contentWindow) return;
    iframe.contentWindow.postMessage({
      source: 'ams_ide',
      type: 'reload'
    }, '*');
  }

  function handleMessage(event) {
    const msg = event.data;
    if (!msg || typeof msg !== 'object') return;
    if (msg.source !== 'ams_engine') return;

    console.log('[PreviewFrame] Engine message:', msg.type);

    switch (msg.type) {
      case 'ready':
        engineReady = true;
        isLoading = false;
        if (Object.keys(projectFiles).length > 0) {
          sendProjectFiles();
        }
        break;

      case 'files_received':
        console.log('[PreviewFrame] Files received:', msg.filesWritten);
        requestReload();
        break;

      case 'reloaded':
        error = null;
        dispatch('reloaded');
        break;

      case 'error':
        error = msg.message;
        dispatch('error', {
          message: msg.message,
          file: msg.file,
          line: msg.line
        });
        break;

      case 'log':
        dispatch('log', { level: msg.level, message: msg.message });
        break;

      case 'pong':
        console.log('[PreviewFrame] Engine alive, IDE mode:', msg.ideMode);
        break;
    }
  }

  function handleLoad() {
    console.log('[PreviewFrame] iframe loaded');
  }

  function handleError() {
    error = 'Failed to load game preview';
    isLoading = false;
  }

  function reload() {
    error = null;
    isLoading = true;
    engineReady = false;
    if (iframe) {
      iframe.src = iframe.src;
    }
  }

  onMount(() => {
    window.addEventListener('message', handleMessage);
  });

  onDestroy(() => {
    window.removeEventListener('message', handleMessage);
    clearTimeout(reloadTimeout);
  });
</script>

<div class="flex flex-col h-full bg-base-100">
  <!-- Toolbar -->
  <div class="flex items-center justify-between px-3 py-1.5 bg-base-200 border-b border-base-300 gap-4">
    <span class="text-xs uppercase font-medium text-base-content/60">Preview</span>
    <div class="flex items-center gap-1.5 text-xs text-base-content/60">
      {#if engineReady}
        <span class="w-2 h-2 rounded-full bg-success"></span>
        <span>Ready</span>
      {:else if isLoading}
        <span class="w-2 h-2 rounded-full bg-warning animate-pulse"></span>
        <span>Loading...</span>
      {:else}
        <span class="w-2 h-2 rounded-full bg-error"></span>
        <span>Disconnected</span>
      {/if}
    </div>
    <div class="flex gap-2">
      <button
        class="btn btn-xs btn-ghost"
        on:click={sendProjectFiles}
        title="Send Files"
        disabled={!engineReady}
      >
        Send
      </button>
      <button class="btn btn-xs btn-ghost" on:click={reload} title="Reload">
        Reload
      </button>
    </div>
  </div>

  <!-- Content -->
  <div class="flex-1 relative overflow-hidden">
    {#if error}
      <div class="absolute inset-0 flex flex-col items-center justify-center bg-base-100/95 z-10">
        <div class="text-center p-8 max-w-md">
          <h3 class="text-error font-semibold mb-4">Error</h3>
          <pre class="bg-base-200 p-4 rounded text-left overflow-x-auto mb-4 text-sm text-base-content">{error}</pre>
          <button class="btn btn-sm btn-outline" on:click={reload}>Retry</button>
        </div>
      </div>
    {/if}

    {#if isLoading && !engineReady}
      <div class="absolute inset-0 flex flex-col items-center justify-center bg-base-100/95 z-10">
        <span class="loading loading-spinner loading-lg text-primary"></span>
        <p class="mt-4 text-base-content/60">Loading game engine...</p>
      </div>
    {/if}

    <iframe
      bind:this={iframe}
      src={engineUrl}
      title="Game Preview"
      on:load={handleLoad}
      on:error={handleError}
      sandbox="allow-scripts allow-same-origin"
      class="w-full h-full border-0 bg-black"
    ></iframe>
  </div>
</div>

<script>
  import CallNode from './lib/profiler/CallNode.svelte';

  let fileInput;
  let profileData = null;
  let error = null;
  let selectedFrame = null;
  let frames = [];

  async function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    error = null;
    profileData = null;
    frames = [];
    selectedFrame = null;

    try {
      const text = await file.text();

      // Profile files can be either:
      // 1. A single JSON object with frames array
      // 2. Newline-delimited JSON (one frame per line)
      // 3. JSON array of frames
      if (text.trim().startsWith('[')) {
        // JSON array of frames
        frames = JSON.parse(text);
      } else if (text.trim().startsWith('{')) {
        // Try parsing as single object or NDJSON
        const lines = text.trim().split('\n');
        if (lines.length === 1) {
          const obj = JSON.parse(text);
          if (obj.frames) {
            frames = obj.frames;
          } else if (obj.type === 'frame') {
            frames = [obj];
          } else {
            frames = [obj];
          }
        } else {
          // NDJSON - one frame per line
          frames = lines
            .filter(line => line.trim())
            .map(line => JSON.parse(line));
        }
      } else {
        throw new Error('Unrecognized profile format');
      }

      profileData = { filename: file.name, frameCount: frames.length };

      if (frames.length > 0) {
        selectedFrame = frames[0];
      }
    } catch (e) {
      error = `Failed to parse profile: ${e.message}`;
    }
  }

  function selectFrame(frame) {
    selectedFrame = frame;
  }

  function formatDuration(ms) {
    if (ms == null) return '—';
    if (ms < 1) return `${(ms * 1000).toFixed(0)}μs`;
    if (ms < 1000) return `${ms.toFixed(2)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  }

  // Build call tree from flat list
  function buildCallTree(calls) {
    if (!calls || calls.length === 0) return [];

    const byId = new Map(calls.map(c => [c.id, { ...c, children: [] }]));
    const roots = [];

    for (const call of calls) {
      const node = byId.get(call.id);
      if (call.parent_id && byId.has(call.parent_id)) {
        byId.get(call.parent_id).children.push(node);
      } else {
        roots.push(node);
      }
    }

    return roots;
  }

  $: callTree = selectedFrame ? buildCallTree(selectedFrame.calls) : [];
  $: totalDuration = selectedFrame?.duration_ms || 1;

  // Selected call for detail view
  let selectedCall = null;

  function handleCallSelect(event) {
    selectedCall = event.detail;
  }

  // Frame timing stats
  $: frameStats = {
    min: frames.length > 0 ? Math.min(...frames.map(f => f.duration_ms)) : 0,
    max: frames.length > 0 ? Math.max(...frames.map(f => f.duration_ms)) : 0,
    avg: frames.length > 0 ? frames.reduce((sum, f) => sum + f.duration_ms, 0) / frames.length : 0,
  };

  // Reset selected call when frame changes
  $: if (selectedFrame) selectedCall = null;
</script>

<div class="min-h-screen bg-base-100 text-base-content">
  <!-- Header -->
  <header class="navbar bg-base-200 border-b border-base-300 px-4">
    <div class="flex-1">
      <span class="text-xl font-bold text-primary">AMS Profile Viewer</span>
      {#if profileData}
        <span class="ml-4 text-sm text-base-content/60">{profileData.filename}</span>
      {/if}
    </div>
    <div class="flex-none gap-4">
      {#if frames.length > 0}
        <div class="text-xs text-base-content/60">
          <span class="text-success">{formatDuration(frameStats.min)}</span> /
          <span class="text-warning">{formatDuration(frameStats.avg)}</span> /
          <span class="text-error">{formatDuration(frameStats.max)}</span>
          <span class="ml-1 opacity-50">(min/avg/max)</span>
        </div>
      {/if}
      <input
        type="file"
        accept=".json,.ndjson,.profile,.jsonl"
        class="hidden"
        bind:this={fileInput}
        on:change={handleFileSelect}
      />
      <button class="btn btn-primary btn-sm" on:click={() => fileInput.click()}>
        Open Profile
      </button>
    </div>
  </header>

  <div class="flex h-[calc(100vh-64px)]">
    <!-- Frame List Sidebar -->
    <aside class="w-72 bg-base-200 border-r border-base-300 flex flex-col">
      <div class="px-3 py-2 border-b border-base-300 flex justify-between items-center">
        <span class="text-xs uppercase text-base-content/50 font-semibold">Frames</span>
        {#if profileData}
          <span class="text-xs text-base-content/50">({frames.length} frames)</span>
        {/if}
      </div>

      <div class="flex-1 overflow-y-auto">
        {#if frames.length > 0}
          {#each frames as frame, i}
            {@const isOver16ms = frame.duration_ms > 16.67}
            {@const isOver33ms = frame.duration_ms > 33.33}
            <button
              class="w-full px-3 py-1.5 text-left text-sm hover:bg-base-300 flex justify-between items-center gap-2"
              class:bg-primary={selectedFrame === frame}
              class:text-primary-content={selectedFrame === frame}
              on:click={() => selectFrame(frame)}
            >
              <span class="font-mono">#{frame.frame ?? i}</span>
              <div class="flex-1 h-2 bg-base-300 rounded overflow-hidden">
                <div
                  class="h-full rounded {isOver33ms ? 'bg-error' : isOver16ms ? 'bg-warning' : 'bg-success'}"
                  style="width: {Math.min((frame.duration_ms / 33.33) * 100, 100)}%"
                ></div>
              </div>
              <span class="text-xs font-mono opacity-60 w-16 text-right">{formatDuration(frame.duration_ms)}</span>
            </button>
          {/each}
        {:else}
          <div class="p-4 text-center text-base-content/50 text-sm">
            No profile loaded
          </div>
        {/if}
      </div>

      <!-- Legend -->
      {#if frames.length > 0}
        <div class="px-3 py-2 border-t border-base-300 text-xs text-base-content/60">
          <div class="flex gap-3">
            <span><span class="inline-block w-2 h-2 bg-success rounded mr-1"></span>&lt;16ms</span>
            <span><span class="inline-block w-2 h-2 bg-warning rounded mr-1"></span>&lt;33ms</span>
            <span><span class="inline-block w-2 h-2 bg-error rounded mr-1"></span>&gt;33ms</span>
          </div>
        </div>
      {/if}
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col overflow-hidden">
      {#if error}
        <div class="alert alert-error m-4">
          <span>{error}</span>
        </div>
      {:else if !profileData}
        <div class="flex-1 flex items-center justify-center">
          <div class="text-center">
            <h2 class="text-2xl font-bold mb-4">Welcome to AMS Profile Viewer</h2>
            <p class="text-base-content/60 mb-6">Load a profile file to analyze game performance</p>
            <button class="btn btn-primary" on:click={() => fileInput.click()}>
              Open Profile File
            </button>
            <p class="text-xs text-base-content/40 mt-4">
              Supports JSON, NDJSON, and .profile formats
            </p>
          </div>
        </div>
      {:else if selectedFrame}
        <!-- Frame Summary -->
        <div class="px-4 py-3 bg-base-200 border-b border-base-300 flex gap-6 items-center">
          <div>
            <span class="text-xs uppercase text-base-content/50">Frame</span>
            <div class="text-lg font-mono">{selectedFrame.frame}</div>
          </div>
          <div>
            <span class="text-xs uppercase text-base-content/50">Duration</span>
            <div class="text-lg font-mono {selectedFrame.duration_ms > 16.67 ? 'text-warning' : 'text-success'}">
              {formatDuration(selectedFrame.duration_ms)}
            </div>
          </div>
          <div>
            <span class="text-xs uppercase text-base-content/50">Calls</span>
            <div class="text-lg font-mono">{selectedFrame.calls?.length ?? 0}</div>
          </div>
          {#if selectedFrame.rollback}
            <div class="badge badge-warning gap-1">
              Rollback
              <span class="font-mono">{selectedFrame.rollback.frames_resimulated} frames</span>
            </div>
          {/if}

          <!-- Color legend -->
          <div class="ml-auto flex gap-3 text-xs">
            <span><span class="inline-block w-3 h-3 bg-green-600 rounded mr-1"></span>Engine</span>
            <span><span class="inline-block w-3 h-3 bg-cyan-600 rounded mr-1"></span>Lua Engine</span>
            <span><span class="inline-block w-3 h-3 bg-blue-600 rounded mr-1"></span>Lua Code</span>
            <span><span class="inline-block w-3 h-3 bg-purple-600 rounded mr-1"></span>Lua Callback</span>
            <span><span class="inline-block w-3 h-3 bg-yellow-600 rounded mr-1"></span>Lua API</span>
          </div>
        </div>

        <!-- Call Tree + Detail Panel -->
        <div class="flex-1 flex overflow-hidden">
          <!-- Call Tree View -->
          <div class="flex-1 overflow-auto p-4">
            {#if callTree.length > 0}
              <div class="space-y-0.5">
                {#each callTree as call}
                  <CallNode
                    {call}
                    {totalDuration}
                    depth={0}
                    selectedId={selectedCall?.id}
                    on:select={handleCallSelect}
                  />
                {/each}
              </div>
            {:else}
              <div class="text-base-content/50 text-sm text-center py-8">
                No calls recorded in this frame
              </div>
            {/if}
          </div>

          <!-- Detail Panel -->
          {#if selectedCall}
            <div class="w-80 border-l border-base-300 bg-base-200 overflow-y-auto">
              <div class="px-3 py-2 border-b border-base-300 flex justify-between items-center">
                <span class="text-xs uppercase text-base-content/50 font-semibold">Call Details</span>
                <button class="btn btn-xs btn-ghost" on:click={() => selectedCall = null}>×</button>
              </div>

              <div class="p-4 space-y-4">
                <!-- Label -->
                <div>
                  <div class="text-xs uppercase text-base-content/50 mb-1">Label</div>
                  <div class="font-mono text-sm break-all">{selectedCall.label}</div>
                </div>

                <!-- Timing -->
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <div class="text-xs uppercase text-base-content/50 mb-1">Duration</div>
                    <div class="font-mono text-lg">{formatDuration(selectedCall.duration)}</div>
                  </div>
                  <div>
                    <div class="text-xs uppercase text-base-content/50 mb-1">Start</div>
                    <div class="font-mono text-lg">{formatDuration(selectedCall.start)}</div>
                  </div>
                </div>

                <!-- Percentage of frame -->
                <div>
                  <div class="text-xs uppercase text-base-content/50 mb-1">% of Frame</div>
                  <div class="flex items-center gap-2">
                    <div class="flex-1 h-2 bg-base-300 rounded overflow-hidden">
                      <div
                        class="h-full bg-primary rounded"
                        style="width: {(selectedCall.duration / totalDuration) * 100}%"
                      ></div>
                    </div>
                    <span class="font-mono text-sm">{((selectedCall.duration / totalDuration) * 100).toFixed(1)}%</span>
                  </div>
                </div>

                <!-- Module & Function -->
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <div class="text-xs uppercase text-base-content/50 mb-1">Module</div>
                    <div class="badge badge-outline">{selectedCall.module}</div>
                  </div>
                  <div>
                    <div class="text-xs uppercase text-base-content/50 mb-1">Function</div>
                    <div class="font-mono text-sm">{selectedCall.func}</div>
                  </div>
                </div>

                <!-- Entity ID -->
                {#if selectedCall.entity_id}
                  <div>
                    <div class="text-xs uppercase text-base-content/50 mb-1">Entity ID</div>
                    <div class="font-mono text-sm bg-base-300 px-2 py-1 rounded">{selectedCall.entity_id}</div>
                  </div>
                {/if}

                <!-- Flags -->
                <div>
                  <div class="text-xs uppercase text-base-content/50 mb-1">Flags</div>
                  <div class="flex gap-2 flex-wrap">
                    {#if selectedCall.lua_code}
                      <span class="badge badge-info badge-sm">Lua Code</span>
                    {/if}
                    {#if selectedCall.lua_callback}
                      <span class="badge badge-secondary badge-sm">Lua Callback</span>
                    {/if}
                    {#if !selectedCall.lua_code && !selectedCall.lua_callback}
                      <span class="badge badge-ghost badge-sm">Python</span>
                    {/if}
                  </div>
                </div>

                <!-- IDs -->
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <div class="text-xs uppercase text-base-content/50 mb-1">Call ID</div>
                    <div class="font-mono text-sm text-base-content/60">{selectedCall.id}</div>
                  </div>
                  <div>
                    <div class="text-xs uppercase text-base-content/50 mb-1">Parent ID</div>
                    <div class="font-mono text-sm text-base-content/60">{selectedCall.parent_id ?? '—'}</div>
                  </div>
                </div>

                <!-- Args -->
                {#if selectedCall.args && Object.keys(selectedCall.args).length > 0}
                  <div>
                    <div class="text-xs uppercase text-base-content/50 mb-1">Arguments</div>
                    <div class="bg-base-300 rounded p-2 font-mono text-xs overflow-x-auto">
                      <pre>{JSON.stringify(selectedCall.args, null, 2)}</pre>
                    </div>
                  </div>
                {/if}

                <!-- Children count -->
                {#if selectedCall.children && selectedCall.children.length > 0}
                  <div>
                    <div class="text-xs uppercase text-base-content/50 mb-1">Child Calls</div>
                    <div class="font-mono text-sm">{selectedCall.children.length}</div>
                  </div>
                {/if}
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </main>
  </div>
</div>

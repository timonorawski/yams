<script>
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  export let logs = [];
  let filter = { level: 'all', search: '' };
  let autoScroll = true;
  let paused = false;
  let logContainer;

  // Auto-truncation settings (default: 200 lines to prevent memory bloat)
  let maxLines = 200;
  const maxLineOptions = [50, 100, 200, 500, 0]; // 0 = unlimited
  let truncatedCount = 0;

  // Apply truncation when logs exceed limit (only when not paused)
  $: if (!paused && maxLines > 0 && logs.length > maxLines) {
    truncatedCount += logs.length - maxLines;
    dispatch('truncate', { count: logs.length - maxLines });
  }

  $: displayLogs = (() => {
    let result = logs;

    // Apply truncation
    if (!paused && maxLines > 0 && result.length > maxLines) {
      result = result.slice(-maxLines);
    }

    // Filter by level
    if (filter.level !== 'all') {
      result = result.filter(l => l.level === filter.level);
    }

    // Filter by search
    if (filter.search) {
      const search = filter.search.toLowerCase();
      result = result.filter(l =>
        l.message.toLowerCase().includes(search) ||
        (l.module && l.module.toLowerCase().includes(search))
      );
    }

    return result;
  })();

  // Auto-scroll to bottom when new logs arrive
  $: if (autoScroll && !paused && logContainer && displayLogs.length) {
    // Use tick to ensure DOM is updated
    setTimeout(() => {
      if (logContainer) {
        logContainer.scrollTop = logContainer.scrollHeight;
      }
    }, 0);
  }

  const levelColors = {
    DEBUG: 'text-base-content/50',
    INFO: 'text-info',
    WARN: 'text-warning',
    WARNING: 'text-warning',
    ERROR: 'text-error'
  };

  const levelBadge = {
    DEBUG: 'badge-ghost',
    INFO: 'badge-info',
    WARN: 'badge-warning',
    WARNING: 'badge-warning',
    ERROR: 'badge-error'
  };

  function formatTime(ts) {
    if (!ts) return '';
    return new Date(ts).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  }

  function clearLogs() {
    dispatch('clear');
    truncatedCount = 0;
  }

  function togglePause() {
    paused = !paused;
    if (!paused) {
      // Resume - scroll to bottom
      autoScroll = true;
    }
  }

  function handleScroll() {
    if (!logContainer) return;
    // If user scrolls up, pause auto-scroll
    const isAtBottom = logContainer.scrollHeight - logContainer.scrollTop <= logContainer.clientHeight + 50;
    if (!isAtBottom && !paused) {
      autoScroll = false;
    } else if (isAtBottom) {
      autoScroll = true;
    }
  }
</script>

<div class="flex flex-col h-full bg-base-200">
  <!-- Toolbar -->
  <div class="flex items-center gap-2 px-2 py-1 border-b border-base-300 text-xs">
    <select class="select select-xs" bind:value={filter.level}>
      <option value="all">All Levels</option>
      <option value="DEBUG">DEBUG</option>
      <option value="INFO">INFO</option>
      <option value="WARN">WARN</option>
      <option value="ERROR">ERROR</option>
    </select>

    <input
      type="text"
      class="input input-xs flex-1 max-w-xs"
      placeholder="Filter logs..."
      bind:value={filter.search}
    />

    <!-- Auto-truncation limit selector -->
    <select class="select select-xs w-20" bind:value={maxLines} title="Max log lines">
      {#each maxLineOptions as opt}
        <option value={opt}>{opt === 0 ? '∞' : opt}</option>
      {/each}
    </select>

    <button
      class="btn btn-xs"
      class:btn-warning={paused}
      on:click={togglePause}
      title={paused ? 'Resume' : 'Pause'}
    >
      {paused ? '▶' : '⏸'}
    </button>

    <label class="flex items-center gap-1 cursor-pointer">
      <input type="checkbox" class="checkbox checkbox-xs" bind:checked={autoScroll} disabled={paused} />
      <span>Auto-scroll</span>
    </label>

    <button class="btn btn-xs btn-ghost" on:click={clearLogs}>Clear</button>

    <!-- Show truncation indicator when logs have been trimmed -->
    {#if truncatedCount > 0}
      <span class="text-warning/70" title="{truncatedCount} older logs removed">
        ({truncatedCount} trimmed)
      </span>
    {/if}

    <span class="text-base-content/50 ml-auto">{displayLogs.length} logs</span>
  </div>

  <!-- Log entries -->
  <div
    class="flex-1 overflow-y-auto font-mono text-xs"
    bind:this={logContainer}
    on:scroll={handleScroll}
  >
    {#if displayLogs.length > 0}
      {#each displayLogs as log, i (log.timestamp + '-' + i)}
        <div class="flex gap-2 px-2 py-0.5 hover:bg-base-300 border-b border-base-300/30">
          <span class="text-base-content/40 w-24 shrink-0">{formatTime(log.timestamp)}</span>
          <span class="badge badge-xs {levelBadge[log.level] || 'badge-ghost'} w-14 shrink-0">{log.level}</span>
          {#if log.module}
            <span class="text-base-content/50 w-24 shrink-0 truncate" title={log.module}>{log.module}</span>
          {/if}
          <span class="{levelColors[log.level] || ''} whitespace-pre-wrap break-all flex-1">{log.message}</span>
        </div>
      {/each}
    {:else}
      <div class="flex items-center justify-center h-full text-base-content/40">
        {#if logs.length === 0}
          No logs yet. Click "Run" to start the game.
        {:else}
          No logs match filter
        {/if}
      </div>
    {/if}
  </div>

  <!-- Paused indicator -->
  {#if paused}
    <div class="px-2 py-1 bg-warning/20 text-warning text-xs text-center">
      Paused - new logs are buffered. Click ▶ to resume.
    </div>
  {/if}
</div>

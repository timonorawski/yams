<script>
  import { createEventDispatcher } from 'svelte';

  export let files = [];

  const dispatch = createEventDispatcher();

  let expandedFolders = new Set(['levels/', 'lua/', 'lua/behaviors/']);

  function toggleFolder(path) {
    if (expandedFolders.has(path)) {
      expandedFolders.delete(path);
    } else {
      expandedFolders.add(path);
    }
    expandedFolders = expandedFolders;
  }

  function selectFile(path) {
    dispatch('select', { path });
  }

  function getIcon(file) {
    if (file.type === 'folder') {
      return expandedFolders.has(file.name) ? '📂' : '📁';
    }
    if (file.name.endsWith('.yaml') || file.name.endsWith('.yml')) {
      return '📄';
    }
    if (file.name.endsWith('.lua')) {
      return '🌙';
    }
    return '📄';
  }
</script>

<div class="h-full flex flex-col">
  <div class="flex-1 overflow-y-auto px-1 py-1">
    {#each files as file}
      <div class="select-none">
        {#if file.type === 'folder'}
          <button
            class="flex items-center gap-1.5 w-full px-2 py-1 bg-transparent text-base-content text-sm text-left cursor-pointer rounded hover:bg-base-300"
            on:click={() => toggleFolder(file.name)}
          >
            <span class="text-sm w-4 text-center">{getIcon(file)}</span>
            <span class="flex-1 truncate">{file.name}</span>
          </button>
          {#if expandedFolders.has(file.name) && file.children}
            <div class="ml-4 border-l border-base-300 pl-2">
              {#each file.children as child}
                {#if child.type === 'folder'}
                  <button
                    class="flex items-center gap-1.5 w-full px-2 py-1 bg-transparent text-base-content text-sm text-left cursor-pointer rounded hover:bg-base-300"
                    on:click={() => toggleFolder(child.name)}
                  >
                    <span class="text-sm w-4 text-center">{getIcon(child)}</span>
                    <span class="flex-1 truncate">{child.name}</span>
                  </button>
                  {#if expandedFolders.has(child.name) && child.children}
                    <div class="ml-4 border-l border-base-300 pl-2">
                      {#each child.children as grandchild}
                        <button
                          class="flex items-center gap-1.5 w-full px-2 py-1 bg-transparent text-base-content text-sm text-left cursor-pointer rounded hover:bg-base-300"
                          on:click={() => selectFile(`${file.name}${child.name}${grandchild.name}`)}
                        >
                          <span class="text-sm w-4 text-center">{getIcon(grandchild)}</span>
                          <span class="flex-1 truncate">{grandchild.name}</span>
                        </button>
                      {/each}
                    </div>
                  {/if}
                {:else}
                  <button
                    class="flex items-center gap-1.5 w-full px-2 py-1 bg-transparent text-base-content text-sm text-left cursor-pointer rounded hover:bg-base-300"
                    on:click={() => selectFile(`${file.name}${child.name}`)}
                  >
                    <span class="text-sm w-4 text-center">{getIcon(child)}</span>
                    <span class="flex-1 truncate">{child.name}</span>
                  </button>
                {/if}
              {/each}
            </div>
          {/if}
        {:else}
          <button
            class="flex items-center gap-1.5 w-full px-2 py-1 bg-transparent text-base-content text-sm text-left cursor-pointer rounded hover:bg-base-300"
            on:click={() => selectFile(file.name)}
          >
            <span class="text-sm w-4 text-center">{getIcon(file)}</span>
            <span class="flex-1 truncate">{file.name}</span>
          </button>
        {/if}
      </div>
    {/each}
  </div>
</div>

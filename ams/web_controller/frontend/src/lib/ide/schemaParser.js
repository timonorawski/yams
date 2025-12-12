/**
 * Schema Content-Type Parser
 *
 * Parses JSON schemas to extract x-content-type annotations,
 * building a map of JSON paths to content types for IDE features.
 */

/**
 * Parse a content type string into structured form
 * @param {string} contentType - e.g., "lua", "@ref:entity_type", "@ref:asset:image|data-uri"
 * @returns {object} Parsed content type
 */
export function parseContentType(contentType) {
  if (!contentType) return null;

  // Handle compound types (pipe-separated)
  if (contentType.includes('|')) {
    return {
      type: 'compound',
      types: contentType.split('|').map(t => parseContentType(t.trim()))
    };
  }

  // Handle reference types (@ref:category or @ref:category:subtype)
  if (contentType.startsWith('@ref:')) {
    const parts = contentType.slice(5).split(':');
    return {
      type: 'reference',
      category: parts[0],
      subtype: parts[1] || null
    };
  }

  // Language/format types (lua, yaml, data-uri, etc.)
  return {
    type: 'language',
    language: contentType
  };
}

/**
 * Content type info with path information
 * @typedef {object} ContentTypeInfo
 * @property {string} path - JSON path (e.g., "entity_types.*.sprite")
 * @property {string} rawType - Original x-content-type value
 * @property {object} parsed - Parsed content type structure
 * @property {string} description - Field description from schema
 */

/**
 * Walk a JSON schema and extract all x-content-type annotations
 * @param {object} schema - JSON schema object
 * @param {string} basePath - Base path for nested schemas (for $ref resolution)
 * @returns {ContentTypeInfo[]} Array of content type info objects
 */
export function extractContentTypes(schema, basePath = '') {
  const results = [];
  const defs = schema.$defs || schema.definitions || {};

  function walk(node, path, visited = new Set()) {
    if (!node || typeof node !== 'object') return;

    // Prevent infinite recursion
    const nodeKey = JSON.stringify({ path, keys: Object.keys(node).sort() });
    if (visited.has(nodeKey)) return;
    visited.add(nodeKey);

    // Check for x-content-type annotation
    if (node['x-content-type']) {
      results.push({
        path: path || '$',
        rawType: node['x-content-type'],
        parsed: parseContentType(node['x-content-type']),
        description: node.description || ''
      });
    }

    // Handle $ref - resolve and continue walking
    if (node.$ref) {
      const resolved = resolveRef(node.$ref, defs);
      if (resolved) {
        walk(resolved, path, new Set(visited));
      }
      return;
    }

    // Walk properties
    if (node.properties) {
      for (const [key, value] of Object.entries(node.properties)) {
        walk(value, path ? `${path}.${key}` : key, new Set(visited));
      }
    }

    // Walk additionalProperties
    if (node.additionalProperties && typeof node.additionalProperties === 'object') {
      walk(node.additionalProperties, path ? `${path}.*` : '*', new Set(visited));
    }

    // Walk items (array)
    if (node.items) {
      if (Array.isArray(node.items)) {
        node.items.forEach((item, i) => {
          walk(item, path ? `${path}[${i}]` : `[${i}]`, new Set(visited));
        });
      } else {
        walk(node.items, path ? `${path}[]` : '[]', new Set(visited));
      }
    }

    // Walk oneOf/anyOf/allOf
    for (const keyword of ['oneOf', 'anyOf', 'allOf']) {
      if (node[keyword]) {
        node[keyword].forEach((subschema, i) => {
          walk(subschema, path, new Set(visited));
        });
      }
    }

    // Walk if/then/else
    if (node.then) walk(node.then, path, new Set(visited));
    if (node.else) walk(node.else, path, new Set(visited));
  }

  // Resolve a $ref to its definition
  function resolveRef(ref, defs) {
    if (ref.startsWith('#/$defs/')) {
      return defs[ref.slice(8)];
    }
    if (ref.startsWith('#/definitions/')) {
      return defs[ref.slice(14)];
    }
    // External refs not supported yet
    return null;
  }

  // Start walking from root
  walk(schema, '');

  // Also walk $defs to capture reusable definitions
  for (const [defName, defSchema] of Object.entries(defs)) {
    walk(defSchema, `$defs.${defName}`);
  }

  return results;
}

/**
 * Build a lookup map from JSON paths to content types
 * @param {ContentTypeInfo[]} contentTypes - Array from extractContentTypes
 * @returns {Map<string, ContentTypeInfo>} Map for quick lookup
 */
export function buildContentTypeMap(contentTypes) {
  const map = new Map();
  for (const info of contentTypes) {
    map.set(info.path, info);
  }
  return map;
}

/**
 * Match a concrete JSON path against patterns with wildcards
 * @param {string} concretePath - Actual path like "entity_types.player.sprite"
 * @param {Map<string, ContentTypeInfo>} contentTypeMap - Map from buildContentTypeMap
 * @returns {ContentTypeInfo|null} Matching content type info or null
 */
export function matchPath(concretePath, contentTypeMap) {
  // Direct match
  if (contentTypeMap.has(concretePath)) {
    return contentTypeMap.get(concretePath);
  }

  // Try wildcard matching
  const parts = concretePath.split('.');
  for (const [pattern, info] of contentTypeMap) {
    if (matchPattern(parts, pattern.split('.'))) {
      return info;
    }
  }

  return null;
}

/**
 * Match path parts against pattern parts with wildcards
 * @param {string[]} pathParts - Concrete path parts
 * @param {string[]} patternParts - Pattern parts (may contain *)
 * @returns {boolean} Whether they match
 */
function matchPattern(pathParts, patternParts) {
  if (pathParts.length !== patternParts.length) return false;

  for (let i = 0; i < pathParts.length; i++) {
    const p = patternParts[i];
    if (p === '*' || p === '[]') continue;
    if (p !== pathParts[i]) return false;
  }

  return true;
}

/**
 * Get all reference categories used in a schema
 * @param {ContentTypeInfo[]} contentTypes - Array from extractContentTypes
 * @returns {Set<string>} Set of reference categories (e.g., "entity_type", "behavior")
 */
export function getReferenceCategories(contentTypes) {
  const categories = new Set();
  for (const info of contentTypes) {
    if (info.parsed.type === 'reference') {
      categories.add(info.parsed.category);
    } else if (info.parsed.type === 'compound') {
      for (const t of info.parsed.types) {
        if (t.type === 'reference') {
          categories.add(t.category);
        }
      }
    }
  }
  return categories;
}

/**
 * Group content types by their type category
 * @param {ContentTypeInfo[]} contentTypes - Array from extractContentTypes
 * @returns {object} Grouped by type: { language: [...], reference: [...], compound: [...] }
 */
export function groupByType(contentTypes) {
  const groups = {
    language: [],
    reference: [],
    compound: []
  };

  for (const info of contentTypes) {
    groups[info.parsed.type].push(info);
  }

  return groups;
}

/**
 * SchemaContentTypeParser class for caching and convenience
 */
export class SchemaContentTypeParser {
  constructor() {
    this.cache = new Map(); // schema URL -> { contentTypes, map }
  }

  /**
   * Fetch and parse a schema, with caching
   * @param {string} schemaUrl - URL to fetch schema from
   * @returns {Promise<{ contentTypes: ContentTypeInfo[], map: Map }>}
   */
  async parse(schemaUrl) {
    if (this.cache.has(schemaUrl)) {
      return this.cache.get(schemaUrl);
    }

    const response = await fetch(schemaUrl);
    if (!response.ok) {
      throw new Error(`Failed to fetch schema: ${response.status}`);
    }

    const schema = await response.json();
    const contentTypes = extractContentTypes(schema);
    const map = buildContentTypeMap(contentTypes);

    const result = { contentTypes, map, schema };
    this.cache.set(schemaUrl, result);
    return result;
  }

  /**
   * Get content type for a specific path in a schema
   * @param {string} schemaUrl - Schema URL
   * @param {string} jsonPath - JSON path to check
   * @returns {Promise<ContentTypeInfo|null>}
   */
  async getContentType(schemaUrl, jsonPath) {
    const { map } = await this.parse(schemaUrl);
    return matchPath(jsonPath, map);
  }

  /**
   * Clear the cache
   */
  clearCache() {
    this.cache.clear();
  }
}

// Default singleton instance
export const schemaParser = new SchemaContentTypeParser();

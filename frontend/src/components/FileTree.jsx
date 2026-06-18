import { useState } from 'react';
import { ChevronRight, ChevronDown, File, Folder } from 'lucide-react';

function parseTree(treeString) {
  if (!treeString) return [];

  const lines = treeString.split('\n');
  const root = { name: 'root', children: [], isDir: true };
  const stack = [{ node: root, depth: -1 }];

  for (const line of lines) {
    const cleaned = line.replace(/[├└│─\s]/g, '');
    if (!cleaned) continue;

    const depth = line.search(/[^\s│├└─]/);
    const name = cleaned.replace(/^\s+/, '');
    const isDir = !name.includes('.');
    const node = { name, children: [], isDir };

    while (stack.length > 1 && stack[stack.length - 1].depth >= depth) {
      stack.pop();
    }

    stack[stack.length - 1].node.children.push(node);
    if (isDir) {
      stack.push({ node, depth });
    }
  }

  return root.children;
}

function TreeNode({ node, depth = 0 }) {
  const [expanded, setExpanded] = useState(depth < 2);

  if (!node.isDir) {
    return (
      <div
        className="flex items-center gap-1.5 py-0.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors cursor-default"
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        <File size={12} className="text-zinc-600 shrink-0" />
        <span className="truncate">{node.name}</span>
      </div>
    );
  }

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-1.5 py-0.5 text-xs text-zinc-300 hover:text-zinc-100 transition-colors cursor-pointer"
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        {expanded ? (
          <ChevronDown size={12} className="text-zinc-500 shrink-0" />
        ) : (
          <ChevronRight size={12} className="text-zinc-600 shrink-0" />
        )}
        <Folder size={12} className="text-violet-400/70 shrink-0" />
        <span className="truncate">{node.name}</span>
      </button>
      {expanded &&
        node.children.map((child, i) => (
          <TreeNode key={`${child.name}-${i}`} node={child} depth={depth + 1} />
        ))}
    </div>
  );
}

export default function FileTree({ treeString }) {
  const [expanded, setExpanded] = useState(false);
  const nodes = parseTree(treeString);

  if (!treeString) return null;

  return (
    <div className="border-t border-zinc-800">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-xs font-medium text-zinc-500 uppercase tracking-wider hover:text-zinc-400 transition-colors cursor-pointer"
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        File tree
      </button>

      {expanded && (
        <div className="px-2 pb-3 max-h-64 overflow-y-auto">
          {nodes.map((node, i) => (
            <TreeNode key={`${node.name}-${i}`} node={node} />
          ))}
        </div>
      )}
    </div>
  );
}

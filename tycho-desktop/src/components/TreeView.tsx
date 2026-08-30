import Tree from 'react-d3-tree';

interface TreeViewProps {
  data: any;
}

export function TreeView({ data }: TreeViewProps) {
  return (
    <div className="w-full h-[500px] border border-gray-200 rounded-lg bg-gray-50 overflow-hidden shadow-inner">
      <Tree 
        data={data} 
        orientation="vertical"
        pathFunc="step"
        translate={{ x: 300, y: 50 }}
        nodeSize={{ x: 120, y: 80 }}
        renderCustomNodeElement={({ nodeDatum, toggleNode }) => (
          <g>
            <circle r={15} fill="#4f46e5" onClick={toggleNode} className="cursor-pointer" />
            <text fill="black" strokeWidth="1" x="20" y="5">
              {nodeDatum.name}
            </text>
          </g>
        )}
      />
    </div>
  );
}

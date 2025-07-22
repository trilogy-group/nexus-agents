'use client';

import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { RefreshCw, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

interface KnowledgeGraphProps {
  projectId: string;
}

interface GraphNode {
  id: string;
  label: string;
  type: 'fact' | 'insight' | 'pov' | 'source';
  level: number;
  x?: number;
  y?: number;
}

interface GraphLink {
  source: string;
  target: string;
  type: 'reference' | 'derived' | 'supports';
}

export function KnowledgeGraph({ projectId }: KnowledgeGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Fetch knowledge graph data
  const { data: graphData, isLoading, refetch } = useQuery({
    queryKey: ['project-knowledge-graph', projectId],
    queryFn: async () => {
      const response = await api.projects.getKnowledgeGraph(projectId);
      return response.data;
    },
  });

  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [links, setLinks] = useState<GraphLink[]>([]);

  // Transform graph data into nodes and links
  useEffect(() => {
    if (!graphData) {
      setNodes([]);
      setLinks([]);
      return;
    }

    const newNodes: GraphNode[] = [];
    const newLinks: GraphLink[] = [];

    // Process DOK levels
    if (graphData.knowledge_tree) {
      graphData.knowledge_tree.forEach((item: any, idx: number) => {
        newNodes.push({
          id: `fact-${idx}`,
          label: item.fact || item.summary || 'Knowledge Item',
          type: 'fact',
          level: item.dok_level || 1,
        });
      });
    }

    if (graphData.insights) {
      graphData.insights.forEach((insight: any, idx: number) => {
        const nodeId = `insight-${idx}`;
        newNodes.push({
          id: nodeId,
          label: insight.insight || 'Insight',
          type: 'insight',
          level: 3,
        });

        // Link to supporting facts
        if (insight.supporting_facts) {
          insight.supporting_facts.forEach((factIdx: number) => {
            if (factIdx < (graphData.knowledge_tree?.length || 0)) {
              newLinks.push({
                source: `fact-${factIdx}`,
                target: nodeId,
                type: 'supports',
              });
            }
          });
        }
      });
    }

    if (graphData.spiky_povs) {
      graphData.spiky_povs.forEach((pov: any, idx: number) => {
        const nodeId = `pov-${idx}`;
        newNodes.push({
          id: nodeId,
          label: pov.statement || 'POV',
          type: 'pov',
          level: 4,
        });

        // Link to insights
        if (pov.supporting_insights) {
          pov.supporting_insights.forEach((insightIdx: number) => {
            if (insightIdx < (graphData.insights?.length || 0)) {
              newLinks.push({
                source: `insight-${insightIdx}`,
                target: nodeId,
                type: 'derived',
              });
            }
          });
        }
      });
    }

    // Layout nodes
    const levels = [1, 2, 3, 4];
    const nodesPerLevel = levels.map(level => newNodes.filter(n => n.level === level));
    
    nodesPerLevel.forEach((levelNodes, levelIdx) => {
      const levelY = 100 + levelIdx * 150;
      levelNodes.forEach((node, nodeIdx) => {
        const totalWidth = 800;
        const spacing = totalWidth / (levelNodes.length + 1);
        node.x = spacing * (nodeIdx + 1);
        node.y = levelY;
      });
    });

    setNodes(newNodes);
    setLinks(newLinks);
  }, [graphData]);

  // Draw the graph
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !graphData) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Apply transformations
    ctx.save();
    ctx.translate(offset.x, offset.y);
    ctx.scale(zoom, zoom);

    // Placeholder visualization
    ctx.fillStyle = '#6B7280';
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    
    // Draw placeholder message
    const centerX = canvas.width / 2 / zoom - offset.x / zoom;
    const centerY = canvas.height / 2 / zoom - offset.y / zoom;
    
    ctx.fillText('Knowledge Graph Visualization', centerX, centerY - 20);
    ctx.fillText('(Implementation in progress)', centerX, centerY + 10);
    
    // Draw DOK levels
    const levels = [
      { y: 100, label: 'DOK 1-2: Facts & Summaries', color: '#3B82F6' },
      { y: 250, label: 'DOK 3: Insights', color: '#10B981' },
      { y: 400, label: 'DOK 4: Spiky POVs', color: '#8B5CF6' },
    ];
    
    levels.forEach(level => {
      ctx.fillStyle = level.color;
      ctx.globalAlpha = 0.1;
      ctx.fillRect(50, level.y - 40, canvas.width - 100, 80);
      ctx.globalAlpha = 1;
      ctx.fillStyle = level.color;
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(level.label, 60, level.y);
    });

    ctx.restore();
  }, [graphData, zoom, offset]);

  // Handle mouse interactions
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(prev => Math.min(Math.max(prev * delta, 0.1), 5));
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setOffset({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="relative h-full">
      {/* Controls */}
      <div className="absolute top-4 right-4 flex gap-2 z-10">
        <button
          onClick={() => refetch()}
          className="p-2 bg-white rounded-lg shadow hover:bg-gray-50"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
        <button
          onClick={() => setZoom(prev => Math.min(prev * 1.2, 5))}
          className="p-2 bg-white rounded-lg shadow hover:bg-gray-50"
          title="Zoom In"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => setZoom(prev => Math.max(prev * 0.8, 0.1))}
          className="p-2 bg-white rounded-lg shadow hover:bg-gray-50"
          title="Zoom Out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => {
            setZoom(1);
            setOffset({ x: 0, y: 0 });
          }}
          className="p-2 bg-white rounded-lg shadow hover:bg-gray-50"
          title="Reset View"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        className="w-full h-full cursor-move"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      />

      {/* Info Panel */}
      {graphData && (
        <div className="absolute bottom-4 left-4 bg-white p-4 rounded-lg shadow max-w-xs">
          <h3 className="font-medium mb-2">Knowledge Graph Stats</h3>
          <div className="space-y-1 text-sm text-gray-600">
            <div>Facts: {graphData.knowledge_tree?.length || 0}</div>
            <div>Insights: {graphData.insights?.length || 0}</div>
            <div>POVs: {graphData.spiky_povs?.length || 0}</div>
            <div>Sources: {graphData.bibliography?.length || 0}</div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Network Topology & Force-Directed Graph Visualizer (Refactored)
 * Provides anti-collision node physics, community cluster separation,
 * neighborhood glow focus, and interactive KOL inspection.
 */

export class NetworkGraphManager {
  constructor(containerId) {
    this.containerId = containerId;
    this.container = document.getElementById(containerId);
    this.network = null;
    this.nodesDataSet = null;
    this.edgesDataSet = null;
    this.rawNetworkData = null;
    this.selectedNodeId = null;
    this.viewMode = 'force'; // 'force' | 'hierarchical' | 'matrix'
  }

  render(networkData) {
    if (!this.container) {
      this.container = document.getElementById(this.containerId);
    }
    if (!this.container) return;
    if (!networkData) return;
    this.rawNetworkData = networkData;

    const visObj = window.vis || (typeof vis !== 'undefined' ? vis : null);
    if (!visObj) {
      // Retry in 300ms if script is still loading
      setTimeout(() => this.render(networkData), 300);
      return;
    }

    // Palette with distinct vibrant community hues
    const communityColors = [
      { bg: '#06b6d4', border: '#22d3ee', glow: 'rgba(6, 182, 212, 0.4)' },
      { bg: '#8b5cf6', border: '#a78bfa', glow: 'rgba(139, 92, 246, 0.4)' },
      { bg: '#10b981', border: '#34d399', glow: 'rgba(16, 185, 129, 0.4)' },
      { bg: '#f59e0b', border: '#fbbf24', glow: 'rgba(245, 158, 11, 0.4)' },
      { bg: '#ec4899', border: '#f472b6', glow: 'rgba(236, 72, 153, 0.4)' },
      { bg: '#3b82f6', border: '#60a5fa', glow: 'rgba(59, 130, 246, 0.4)' }
    ];

    // Map backend nodes into clean, non-overlapping Vis nodes
    const visNodes = (networkData.nodes || []).map(node => {
      const commIdx = (node.community || 0) % communityColors.length;
      const col = communityColors[commIdx];
      const cleanSize = Math.max(14, Math.min(26, Math.round(12 + (node.influence_score || 50) * 0.14)));

      return {
        id: node.id,
        label: `@${node.id}\n${node.influence_score}★`,
        title: `<div style="padding:6px; font-family: Outfit, sans-serif; font-size:12px;">` +
               `<strong style="color:${col.border}; font-size:13px;">${node.name}</strong> (@${node.id})<br/>` +
               `Role: <b>${node.role || 'Audience Node'}</b><br/>` +
               `Influence Score: <b>${node.influence_score} / 100</b><br/>` +
               `Followers: <b>${(node.followers || 0).toLocaleString()}</b><br/>` +
               `PageRank: <b>${node.pagerank || 0}</b> | In-Degree: <b>${node.in_degree || 0}</b>` +
               `</div>`,
        shape: 'dot',
        size: cleanSize,
        color: {
          background: col.bg,
          border: '#ffffff',
          highlight: {
            background: '#ffffff',
            border: col.border
          },
          hover: {
            background: col.border,
            border: '#ffffff'
          }
        },
        borderWidth: 2,
        borderWidthSelected: 3,
        shadow: {
          enabled: true,
          color: col.glow,
          size: 12,
          x: 0,
          y: 0
        },
        font: {
          face: 'Outfit, sans-serif',
          size: 11,
          color: '#f8fafc',
          strokeWidth: 3,
          strokeColor: '#07090e',
          vadjust: 2
        },
        margin: 8,
        data: node
      };
    });

    // Map edges with directional arrows and sentiment coloration
    const visEdges = (networkData.edges || []).map((edge, idx) => {
      const isPos = edge.sentiment > 0.05;
      const isNeg = edge.sentiment < -0.05;
      const strokeColor = isPos 
        ? 'rgba(16, 185, 129, 0.75)' 
        : (isNeg ? 'rgba(244, 63, 94, 0.75)' : 'rgba(6, 182, 212, 0.55)');

      return {
        id: `edge_${idx}`,
        from: edge.from,
        to: edge.to,
        arrows: {
          to: {
            enabled: true,
            scaleFactor: 0.65
          }
        },
        color: {
          color: strokeColor,
          highlight: '#00f0ff',
          hover: '#ffffff',
          opacity: 0.85
        },
        width: Math.max(1.5, Math.min(4.0, 1 + (edge.weight || 1) * 0.5)),
        smooth: {
          type: 'continuous',
          roundness: 0.2
        },
        selectionWidth: 2.5
      };
    });

    this.nodesDataSet = new visObj.DataSet(visNodes);
    this.edgesDataSet = new visObj.DataSet(visEdges);

    // Physics Engine with Anti-Collision / Collision Avoidance
    const options = {
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -140,
          centralGravity: 0.015,
          springLength: 160,
          springConstant: 0.08,
          damping: 0.75,
          avoidOverlap: 1.0
        },
        stabilization: {
          enabled: true,
          iterations: 150,
          updateInterval: 25
        }
      },
      interaction: {
        hover: true,
        hoverConnectedEdges: true,
        selectConnectedEdges: true,
        tooltipDelay: 120,
        zoomView: true,
        dragView: true,
        multiselect: false
      },
      nodes: {
        chosen: {
          node: (values, id, selected, hovering) => {
            if (selected || hovering) {
              values.shadowSize = 25;
              values.borderWidth = 3;
            }
          }
        }
      }
    };

    // Instantiate or update Vis Network
    if (this.network) {
      try {
        this.network.setData({ nodes: this.nodesDataSet, edges: this.edgesDataSet });
        this.network.setOptions(options);
        setTimeout(() => {
          if (this.network) {
            this.network.redraw();
            this.network.fit();
          }
        }, 80);
        return;
      } catch (e) {
        this.network = null;
      }
    }

    this.network = new visObj.Network(
      this.container,
      { nodes: this.nodesDataSet, edges: this.edgesDataSet },
      options
    );

    setTimeout(() => {
      if (this.network) {
        this.network.redraw();
        this.network.fit();
      }
    }, 150);

    // Click handler for node selection & neighborhood focus
    this.network.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        this.selectedNodeId = nodeId;
        this.focusNeighborhood(nodeId);
        const nodeInfo = (networkData.nodes || []).find(n => n.id === nodeId);
        if (nodeInfo && window.onNodeSelected) {
          window.onNodeSelected(nodeInfo);
        }
      } else {
        this.resetFocus();
      }
    });

    // Hover effect: highlight connected edges
    this.network.on('hoverNode', () => {
      if (this.container) this.container.style.cursor = 'pointer';
    });
  }

  /**
   * Highlights direct neighbors of selected node and softly dims other nodes
   */
  focusNeighborhood(selectedNodeId) {
    if (!this.network || !this.nodesDataSet || !this.edgesDataSet) return;

    const connectedNodes = this.network.getConnectedNodes(selectedNodeId);
    const connectedEdges = this.network.getConnectedEdges(selectedNodeId);
    const allNodeIds = new Set([selectedNodeId, ...connectedNodes]);

    // Update nodes opacity/glow
    const nodeUpdates = [];
    this.nodesDataSet.forEach(node => {
      if (allNodeIds.has(node.id)) {
        nodeUpdates.push({
          id: node.id,
          opacity: 1.0,
          font: { color: '#ffffff', strokeColor: '#07090e', strokeWidth: 3 }
        });
      } else {
        nodeUpdates.push({
          id: node.id,
          opacity: 0.2,
          font: { color: 'rgba(255,255,255,0.2)', strokeWidth: 0 }
        });
      }
    });
    this.nodesDataSet.update(nodeUpdates);

    // Update edges opacity
    const edgeUpdates = [];
    this.edgesDataSet.forEach(edge => {
      if (connectedEdges.includes(edge.id)) {
        edgeUpdates.push({ id: edge.id, color: { opacity: 0.95 } });
      } else {
        edgeUpdates.push({ id: edge.id, color: { opacity: 0.08 } });
      }
    });
    this.edgesDataSet.update(edgeUpdates);
  }

  /**
   * Resets all nodes and edges to full visibility
   */
  resetFocus() {
    if (!this.nodesDataSet || !this.edgesDataSet) return;
    this.selectedNodeId = null;

    const nodeUpdates = [];
    this.nodesDataSet.forEach(node => {
      nodeUpdates.push({
        id: node.id,
        opacity: 1.0,
        font: { color: '#f8fafc', strokeWidth: 3, strokeColor: '#07090e' }
      });
    });
    this.nodesDataSet.update(nodeUpdates);

    const edgeUpdates = [];
    this.edgesDataSet.forEach(edge => {
      edgeUpdates.push({ id: edge.id, color: { opacity: 0.8 } });
    });
    this.edgesDataSet.update(edgeUpdates);
  }

  highlightKOL(nodeId) {
    if (!this.network) return;
    this.network.focus(nodeId, {
      scale: 1.25,
      animation: { duration: 600, easingFunction: 'easeInOutQuad' }
    });
    this.network.selectNodes([nodeId]);
    this.focusNeighborhood(nodeId);
  }

  setPhysicsMode(mode) {
    if (!this.network) return;
    if (mode === 'hierarchical') {
      this.network.setOptions({
        layout: {
          hierarchical: {
            enabled: true,
            direction: 'UD',
            sortMethod: 'directed',
            nodeSpacing: 180,
            levelSeparation: 140
          }
        },
        physics: { enabled: false }
      });
    } else {
      this.network.setOptions({
        layout: { hierarchical: { enabled: false } },
        physics: {
          enabled: true,
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {
            gravitationalConstant: -160,
            centralGravity: 0.012,
            springLength: 170,
            springConstant: 0.08,
            damping: 0.72,
            avoidOverlap: 1.0
          }
        }
      });
    }
  }

  async animateCascade(cascadeTimeline, seedId = null) {
    if (!this.network || !cascadeTimeline) return;
    const steps = Array.isArray(cascadeTimeline) ? cascadeTimeline : (cascadeTimeline.steps || []);
    if (steps.length === 0) return;

    // First highlight seed node
    if (seedId && this.nodesDataSet.get(seedId)) {
      this.nodesDataSet.update({
        id: seedId,
        color: { background: '#f43f5e', border: '#ffffff' },
        shadow: { color: '#f43f5e', size: 30 }
      });
      this.network.focus(seedId, { scale: 1.15, animation: { duration: 400 } });
    }

    for (const step of steps) {
      const propagations = step.propagations || [];
      const stepNodes = propagations.map(p => p.to_node);
      
      stepNodes.forEach(nId => {
        if (this.nodesDataSet.get(nId)) {
          this.nodesDataSet.update({
            id: nId,
            color: { background: '#ec4899', border: '#ffffff' },
            shadow: { color: '#ec4899', size: 25 }
          });
        }
      });

      // Highlight active edges
      const edgeUpdates = [];
      propagations.forEach(p => {
        this.edgesDataSet.forEach(e => {
          if ((e.from === p.from_node && e.to === p.to_node) || (e.from === p.to_node && e.to === p.from_node)) {
            edgeUpdates.push({ id: e.id, color: { color: '#ec4899', highlight: '#f43f5e', opacity: 1.0 }, width: 4.5 });
          }
        });
      });
      if (edgeUpdates.length > 0) {
        this.edgesDataSet.update(edgeUpdates);
      }

      await new Promise(r => setTimeout(r, 700));
    }
  }
}

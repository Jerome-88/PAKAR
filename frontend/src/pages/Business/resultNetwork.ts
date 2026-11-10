import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type SimulationNodeDatum } from "d3-force";

export type ResultNetworkNode = SimulationNodeDatum & { id: string; x: number; y: number };

export function createResultNetwork(ids: string[], edges: { source: string; target: string }[], width: number) {
  const worldWidth = Math.max(680, width, Math.sqrt(ids.length) * 150);
  const height = Math.max(480, Math.sqrt(ids.length) * 130);
  const radius = Math.max(120, Math.min(worldWidth, height) * .32);
  const nodes: ResultNetworkNode[] = ids.map((id, index) => ({ id, x: worldWidth / 2 + Math.cos(index * Math.PI * 2 / ids.length - Math.PI / 2) * radius, y: height / 2 + Math.sin(index * Math.PI * 2 / ids.length - Math.PI / 2) * radius }));
  const links = edges.map(edge => ({ ...edge }));
  // D3's seeded simulation starts from the same positions for the same IDs.
  // Settle once rather than running an animation loop for every render.
  const simulation = forceSimulation(nodes).force("links", forceLink<ResultNetworkNode, typeof links[number]>(links).id(node => node.id).distance(145).strength(.24)).force("charge", forceManyBody().strength(-220)).force("collision", forceCollide(62)).force("center", forceCenter(worldWidth / 2, height / 2)).force("x", forceX(worldWidth / 2).strength(.045)).force("y", forceY(height / 2).strength(.06)).stop();
  for (let tick = 0; tick < 180; tick++) simulation.tick();
  const byId = new Map(nodes.map(node => [node.id, node]));
  return { nodes, byId, width: worldWidth, height, initial: new Map(nodes.map(node => [node.id, { x: node.x, y: node.y }])) };
}

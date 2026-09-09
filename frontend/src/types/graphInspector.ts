export interface NodePropertyItem {
  key: string;
  value: string;
}

export interface GraphNodeDetail {
  id: string;
  label: string; // Character, Item, Location, Faction, Event, Concept
  properties: Record<string, string>;
}

export type InspectorMode = 'view' | 'edit';

export interface EdgeCreationPayload {
  source: string;
  target: string;
  type: string;
  properties?: Record<string, unknown>;
}
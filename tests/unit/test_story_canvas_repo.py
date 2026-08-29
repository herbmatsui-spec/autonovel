import { describe, it, expect, vi, beforeEach } from 'vitest';
import { StoryCanvasRepository } from './story_canvas_repo';
import { StoryNode, StoryEdge } from '../../models';

describe('StoryCanvasRepository', () => {
  let repo: StoryCanvasRepository;
  let mockSession: any;

  beforeEach(() => {
    mockSession = {
      execute: vi.fn(),
      flush: vi.fn(),
    };
    repo = new StoryCanvasRepository(mockSession as any);
  });

  describe('get_nodes', () => {
    it('should return empty array when no nodes found', async () => {
      mockSession.execute.mockResolvedValue({
        scalars: () => ({
          all: () => [],
        }),
      });

      const result = await repo.get_nodes(1);
      expect(result).toEqual([]);
    });

    it('should parse nodes correctly', async () => {
      const mockRow = {
        id: 1,
        book_id: 1,
        kind: 'episode',
        label: 'Test Node',
        ep_num: 1,
        character_id: null,
        x: 100,
        y: 200,
        data: '{"test": "value"}',
      };
      mockSession.execute.mockResolvedValue({
        scalars: () => ({
          all: () => [mockRow],
        }),
      });

      const result = await repo.get_nodes(1);
      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({
        id: 'node-1',
        book_id: 1,
        kind: 'episode',
        label: 'Test Node',
        ep_num: 1,
        character_id: null,
        x: 100,
        y: 200,
        data: { test: 'value' },
      });
    });
  });

  describe('upsert_node', () => {
    it('should create new node when node_id not provided', async () => {
      mockSession.execute.mockResolvedValue({});
      mockSession.flush.mockResolvedValue({});

      const result = await repo.upsert_node(
        1,
        'episode',
        'Test Node',
        100,
        200,
        { test: 'value' },
        1,
        null
      );

      expect(mockSession.execute).toHaveBeenCalled();
      expect(mockSession.flush).toHaveBeenCalled();
      expect(result).toBeInstanceOf(Object);
    });

    it('should update existing node when node_id provided', async () => {
      const existingNode = {
        id: 1,
        book_id: 1,
        kind: 'episode',
        label: 'Old Label',
        ep_num: 1,
        character_id: null,
        x: 50,
        y: 100,
        data: { old: 'value' },
      };
      mockSession.execute.mockResolvedValue({
        scalar_one_or_none: () => existingNode,
      });
      mockSession.flush.mockResolvedValue({});

      const result = await repo.upsert_node(
        1,
        'episode',
        'New Label',
        150,
        250,
        { new: 'value' },
        undefined,
        1
      );

      expect(mockSession.execute).toHaveBeenCalled();
      expect(mockSession.flush).toHaveBeenCalled();
      // Note: In real implementation, this would return the updated node
    });
  });

  describe('create_edge', () => {
    it('should create edge successfully', async () => {
      mockSession.execute.mockResolvedValue({});
      mockSession.flush.mockResolvedValue({});

      const result = await repo.create_edge(
        1,
        'node-1',
        'node-2',
        'flow',
        { strength: 0.8 }
      );

      expect(mockSession.execute).toHaveBeenCalled();
      expect(mockSession.flush).toHaveBeenCalled();
      expect(result).toBeInstanceOf(Object);
    });
  });
});
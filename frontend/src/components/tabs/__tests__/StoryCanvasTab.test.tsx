import { render, screen, fireEvent } from '@testing-library/react';
import { StoryCanvasTab } from '@/components/tabs/StoryCanvasTab';
import { useBookStore } from '@/store/useBookStore';
import { useStoryCanvasStore } from '@/store/useStoryCanvasStore';
import { seedStoryCanvas } from '@/api';

// Mock the stores and API
vi.mock('@/store/useBookStore');
vi.mock('@/store/useStoryCanvasStore');
vi.mock('@/api');

describe('StoryCanvasTab', () => {
  const mockBookStore = useBookStore as jest.Mock;
  const mockCanvasStore = useStoryCanvasStore as jest.Mock;
  const mockSeedStoryCanvas = seedStoryCanvas as jest.Mock;

  beforeEach(() => {
    mockBookStore.mockReturnValue({
      selectedBook: { id: 1, title: 'Test Book' },
    });

    mockCanvasStore.mockReturnValue({
      nodes: [],
      edges: [],
      selectedId: null,
      loading: false,
      setLoading: vi.fn(),
      panX: 0,
      panY: 0,
      scale: 1,
      setPan: vi.fn(),
      setScale: vi.fn(),
      resetViewport: vi.fn(),
      addNode: vi.fn(),
      moveNode: vi.fn(),
      renameNode: vi.fn(),
      updateNodeData: vi.fn(),
      removeNode: vi.fn(),
      addEdge: vi.fn(),
      removeEdge: vi.fn(),
      setSelected: vi.fn(),
      dirty: false,
    });

    mockSeedStoryCanvas.mockResolvedValue(undefined);
  });

  it('renders the canvas tab header', () => {
    render(<StoryCanvasTab />);

    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(
      'ストーリーキャンバス - Test Book'
    );
    expect(screen.getByText(/エピソード・キャラクター・構造を視覚的に編集/)).toBeInTheDocument();
  });

  it('shows seeding button', () => {
    render(<StoryCanvasTab />);

    const seedButton = screen.getByRole('button', { name: /🌱 キャンバスを初期化 \(Seed\)/ });
    expect(seedButton).toBeInTheDocument();
  });

  it('calls seedStoryCanvas when seed button is clicked', async () => {
    render(<StoryCanvasTab />);

    const seedButton = screen.getByRole('button', { name: /🌱 キャンバスを初期化 \(Seed\)/ });
    await fireEvent.click(seedButton);

    expect(mockSeedStoryCanvas).toHaveBeenCalledWith(1);
  });

  it('shows "no book selected" message when no book', () => {
    mockBookStore.mockReturnValue({
      selectedBook: null,
    });

    render(<StoryCanvasTab />);

    expect(screen.getByText(/作品を選択してください/)).toBeInTheDocument();
  });

  it('renders toolbar buttons', () => {
    render(<StoryCanvasTab />);

    expect(screen.getByRole('button', { name: /+エピソード/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /+キャラクター/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /リンクモード \(L\)/ })).toBeInTheDocument();
  });
});
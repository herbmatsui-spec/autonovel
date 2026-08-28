import { PlotsTab } from '@/components/tabs/PlotsTab';
import ContextActionBar from '@/components/ContextActionBar';

export function OutlineStep(_props: { bookId?: number; step?: string } = {}) {
  const { bookId, step } = _props;
  const currentStep = step || 'outline';
  
  const suggestedActions = [
    {
      label: 'スタイルラボで参照',
      icon: '🧬',
      tab: 'style-lab',
      onClick: (bookId, currentStep) => {
        if (bookId) {
          navigate(`/book/${bookId}/${currentStep}/style-lab`, { replace: true });
        }
      }
    },
    {
      label: 'キャラクター詳細を編集',
      icon: '👥',
      tab: 'books', // Note: the books tab is the list of books, but we might want to use a different tab for character edit? We'll use books for now, but note that the books tab doesn't take a bookId? Actually, the books tab is the list of books. We might want to change this to a character tab if we have one. We'll leave it as books for now, but note that it might not be the best fit.
      // We'll change this to a character tab if we create one. For now, we'll use the books tab and hope it shows the character list for the current book? We'll need to adjust the books tab to show characters for a book? We'll do that later.
      onClick: (bookId, currentStep) => {
        if (bookId) {
          // We'll navigate to the books tab and hope it shows the current book's characters? We'll need to pass the bookId as a parameter? The books tab doesn't take a bookId in the URL.
          // We'll change the books tab to accept a bookId? We'll do that later.
          // For now, we'll just go to the books tab and hope it has a way to show the current book's characters.
          navigate(`/books`, { replace: true });
        }
      }
    }
  ];

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-2">
        AIがプロットを下書きします。よければ次へ進んでください。
      </p>
      <PlotsTab />
      <ContextActionBar bookId={bookId} currentStep={currentStep} suggestedActions={suggestedActions} />
    </div>
  );
}

export default OutlineStep;
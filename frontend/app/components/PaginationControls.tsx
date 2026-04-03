// app/components/PaginationControls.tsx
import React from 'react';
import { ChevronFirst, ChevronLast, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './ui/button';

interface PaginationControlsProps {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  onPageChange: (newPage: number) => void;
  isLoading: boolean;
}

const PaginationControls: React.FC<PaginationControlsProps> = ({
  currentPage,
  totalPages,
  totalItems,
  onPageChange,
  isLoading
}) => {
  // Show page 0 if there are no results
  const displayPage = totalItems === 0 ? 0 : currentPage;
  const displayTotalPages = totalItems === 0 ? 0 : totalPages;

  return (
    <div className="flex flex-col sm:flex-row justify-between items-center gap-2">
      <div className="text-sm text-gray-600 dark:text-gray-300 flex items-center gap-2">
        <span>Pagina {displayPage} di {displayTotalPages}</span>
        <span className="text-gray-400">•</span>
        <span>{totalItems.toLocaleString('it-IT')} Copertine</span>
      </div>
      
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon"
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1 || isLoading || totalItems === 0}
          className="w-8 h-8 hover:text-red-600 dark:hover:text-red-400 hover:border-red-200 dark:hover:border-red-900"
          title="Prima pagina"
        >
          <ChevronFirst className="h-4 w-4" />
        </Button>
        
        <Button
          variant="outline"
          size="icon"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1 || isLoading || totalItems === 0}
          className="w-8 h-8 hover:text-red-600 dark:hover:text-red-400 hover:border-red-200 dark:hover:border-red-900"
          title="Pagina precedente"
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        
        <Button
          variant="outline"
          size="icon"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages || isLoading || totalItems === 0}
          className="w-8 h-8 hover:text-red-600 dark:hover:text-red-400 hover:border-red-200 dark:hover:border-red-900"
          title="Pagina successiva"
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        
        <Button
          variant="outline"
          size="icon"
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages || isLoading || totalItems === 0}
          className="w-8 h-8 hover:text-red-600 dark:hover:text-red-400 hover:border-red-200 dark:hover:border-red-900"
          title="Ultima pagina"
        >
          <ChevronLast className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
};

export default PaginationControls;
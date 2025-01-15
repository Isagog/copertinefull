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
  return (
    <div className="border-t-2 border-red-500 bg-white dark:bg-gray-800 py-2 px-4">
      <div className="flex flex-col sm:flex-row justify-between items-center gap-2">
        <div className="text-sm text-gray-600 dark:text-gray-300 flex items-center gap-2">
          <span>Pagina {currentPage} di {totalPages}</span>
          <span className="text-gray-400">•</span>
          <span>{totalItems.toLocaleString('it-IT')} Copertine</span>
        </div>
        
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            onClick={() => onPageChange(1)}
            disabled={currentPage === 1 || isLoading}
            className="w-8 h-8 border-gray-300 dark:border-gray-600"
            title="Prima pagina"
          >
            <ChevronFirst className="h-4 w-4" />
          </Button>
          
          <Button
            variant="outline"
            size="icon"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1 || isLoading}
            className="w-8 h-8 border-gray-300 dark:border-gray-600"
            title="Pagina precedente"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          
          <Button
            variant="outline"
            size="icon"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages || isLoading}
            className="w-8 h-8 border-gray-300 dark:border-gray-600"
            title="Pagina successiva"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          
          <Button
            variant="outline"
            size="icon"
            onClick={() => onPageChange(totalPages)}
            disabled={currentPage === totalPages || isLoading}
            className="w-8 h-8 border-gray-300 dark:border-gray-600"
            title="Ultima pagina"
          >
            <ChevronLast className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default PaginationControls;
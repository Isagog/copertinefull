// app/components/copertina/CopertinaCard.tsx
import { useState, useEffect } from "react";
import { CopertineEntry } from "@app/types/copertine";
import Image from "next/image";

interface CopertinaCardProps {
  copertina: CopertineEntry;
}

// Italian month names
const months = [
  'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
  'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
];

// Italian day names
const days = [
  'Domenica', 'Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato'
];

function formatItalianDate(isoDate: string): string {
  const date = new Date(isoDate);
  const dayName = days[date.getDay()];
  const day = date.getDate();
  const month = months[date.getMonth()];
  const year = date.getFullYear();
  
  return `${dayName}, ${day} ${month} ${year}`;
}

export default function CopertinaCard({ copertina }: CopertinaCardProps) {
  const [isPopupVisible, setIsPopupVisible] = useState(false);

  const imagePath = `/images/${copertina.filename}`;
  const formattedDate = formatItalianDate(copertina.isoDate);

  const togglePopup = () => {
    setIsPopupVisible(!isPopupVisible);
  };

  const closePopup = () => {
    setIsPopupVisible(false);
  };

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closePopup();
      }
    };

    if (isPopupVisible) {
      document.addEventListener("keydown", handleKeyDown);
    } else {
      document.removeEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isPopupVisible]);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200 p-6 border border-gray-100 dark:border-gray-700 max-w-4xl w-full">
      <div className="space-y-6">
        {/* Title and Date row */}
        <div className="flex flex-wrap items-center gap-2 text-lg">
          <div className="font-semibold text-gray-900 dark:text-gray-100">
            {copertina.extracted_caption}
          </div>
          <span className="text-gray-600 dark:text-gray-300">-</span>
          <div className="text-gray-600 dark:text-gray-300">
            {formattedDate}
          </div>
        </div>

        {/* Image and Kicker container */}
        <div className="flex gap-6">
          {/* Image - reduced width from 400px to 288px (w-72) */}
          <div className="flex-shrink-0 w-72">
            <div 
              className="relative aspect-[4/3] w-full rounded-lg overflow-hidden cursor-pointer hover:opacity-90 transition-opacity"
              onClick={togglePopup}
            >
              <Image
                src={imagePath}
                alt={copertina.extracted_caption}
                fill
                className="object-cover"
              />
            </div>
          </div>

          {/* Kicker Text - constrained width */}
          <div className="max-w-lg text-lg leading-relaxed text-gray-700 dark:text-gray-300">
            <p className="text-justify">
              {copertina.kickerStr}
            </p>
          </div>
        </div>
      </div>

      {isPopupVisible && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={closePopup}
        >
          {/* Replace everything from here... */}
          <div
            className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-4 relative max-w-4xl w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={closePopup}
              className="absolute top-2 right-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              aria-label="Close popup"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
            <Image
              src={imagePath}
              alt={copertina.extracted_caption}
              width={1200}
              height={900}
              className="rounded cursor-pointer"
              onClick={closePopup}
            />
          </div>
          {/* ...to here */}
        </div>
      )}
    </div>
  );
}

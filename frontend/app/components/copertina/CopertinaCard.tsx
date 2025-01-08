import { useState, useEffect } from "react";
import { CopertineEntry } from "@/app/types/copertine";
import Image from "next/image";

interface CopertinaCardProps {
  copertina: CopertineEntry;
}

export default function CopertinaCard({ copertina }: CopertinaCardProps) {
  const [isPopupVisible, setIsPopupVisible] = useState(false);

  const imagePath = `/data/copertine/${copertina.filename}`;
  const eyeIconPath = `/icons8-eye-50.png`;

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
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200 p-6 border border-gray-100 dark:border-gray-700 relative">
      <div className="space-y-4">
        {/* Date and Caption row */}
        <div className="flex items-center gap-4 pb-4 border-b border-gray-100 dark:border-gray-700">
          <div className="text-lg text-gray-600 dark:text-gray-300 flex-shrink-0">
            {copertina.date}
          </div>
          <div className="text-xl font-semibold text-gray-900 dark:text-gray-100 flex-grow">
            {copertina.extracted_caption}
          </div>
          <button
            onClick={togglePopup}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            aria-label="View image"
          >
            <Image src={eyeIconPath} alt="View Image" width={24} height={24} />
          </button>
        </div>

        {/* Description */}
<div className="flex items-start gap-4 text-lg leading-relaxed text-gray-700 dark:text-gray-300">
  <Image
    src="/mema.svg" // Replace with the actual path to the "MeMa" icon
    alt="MeMa Icon"
    width={50} // Increased size
    height={50}
    className="flex-shrink-0 self-start" // Ensures the icon aligns with the top of the text
  />
  <p className="text-justify">
    {copertina.image_description}
  </p>
</div>
      </div>

      {/* Popup Modal */}
      {isPopupVisible && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={closePopup} // Close when clicking outside the modal
        >
          <div
            className="bg-white dark:bg-gray-900 rounded-lg shadow-lg p-4 relative max-w-2xl w-full"
            onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside the modal
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
              width={800}
              height={600}
              className="rounded cursor-pointer"
              onClick={closePopup} // Close when clicking on the image
            />
          </div>
        </div>
      )}
    </div>
  );
}

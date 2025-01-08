// app/types/copertine.ts
export interface CopertineData {
    model: string;
    extracted_caption: string;
    image_description: string;
    date: string;
    extraction_timestamp: string;
  }
  
  export interface CopertineEntry extends CopertineData {
    filename: string;
  }
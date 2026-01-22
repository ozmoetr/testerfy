import { useState, useEffect, useRef } from "react";
import ColorThief from "colorthief";

export function useAlbumColor(imageUrl: string | undefined) {
  const [color, setColor] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const lastUrlRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!imageUrl) {
      setColor(null);
      return;
    }

    if (imageUrl === lastUrlRef.current) {
      return;
    }
    lastUrlRef.current = imageUrl;

    let active = true;
    setIsLoading(true);
    const img = new Image();
    img.crossOrigin = "anonymous";

    img.onload = () => {
      if (!active) return;
      try {
        const colorThief = new ColorThief();
        const dominantColor = colorThief.getColor(img);
        if (dominantColor) {
          const [r, g, b] = dominantColor;
          setColor(`rgba(${r}, ${g}, ${b}, 0.2)`);
        }
      } catch (err) {
        console.error("Failed to extract color:", err);
        setColor(null);
      }
      setIsLoading(false);
    };

    img.onerror = () => {
      if (!active) return;
      setIsLoading(false);
      setColor(null);
    };

    img.src = imageUrl;

    return () => {
      active = false;
      img.onload = null;
      img.onerror = null;
    };
  }, [imageUrl]);

  return { color, isLoading };
}

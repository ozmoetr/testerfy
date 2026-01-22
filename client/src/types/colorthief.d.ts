declare module 'colorthief' {
  export default class ColorThief {
    getColor(img: HTMLImageElement, quality?: number): [number, number, number] | null;
    getPalette(img: HTMLImageElement, colorCount?: number, quality?: number): [number, number, number][] | null;
  }
}

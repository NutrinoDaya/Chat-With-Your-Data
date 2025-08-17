declare module '*.scss' {
  const content: { [className: string]: string } | string;
  export default content;
}

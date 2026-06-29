import { useEffect } from "react";

type SEOProps = {
  title: string;
  description?: string;
};

function SEO({ title, description }: SEOProps) {
  useEffect(() => {
    document.title = `${title} · CodeAtlas`;

    if (description) {
      let meta = document.querySelector<HTMLMetaElement>('meta[name="description"]');
      if (!meta) {
        meta = document.createElement("meta");
        meta.name = "description";
        document.head.appendChild(meta);
      }
      meta.content = description;
    }
  }, [title, description]);

  return null;
}

export default SEO;

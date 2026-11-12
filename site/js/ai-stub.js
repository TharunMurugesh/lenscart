/* OFFLINE FALLBACK ONLY. Used when the real model (ai/lensnet.onnx) cannot load.
 * Returns FIXED FAKE predictions so the page can be shown working; the UI labels them as demo data. */
window.LensAIStub = {
  async analyze(img) {
    const c = document.createElement("canvas");
    c.width = c.height = 224;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, 224, 224);
    const w = img.naturalWidth, h = img.naturalHeight, s = 224 / Math.max(w, h);
    ctx.drawImage(img, (224 - w * s) / 2, (224 - h * s) / 2, w * s, h * s);
    const fake = {
      articleType: [{ label: "Tshirts", p: 0.5 }, { label: "Shirts", p: 0.3 }, { label: "Tops", p: 0.2 }],
      baseColour: [{ label: "Blue", p: 0.5 }, { label: "Navy Blue", p: 0.3 }, { label: "Black", p: 0.2 }],
      gender: [{ label: "Men", p: 0.6 }, { label: "Unisex", p: 0.3 }, { label: "Women", p: 0.1 }],
      usage: [{ label: "Casual", p: 0.7 }, { label: "Sports", p: 0.2 }, { label: "Formal", p: 0.1 }],
    };
    return Object.assign(fake, { heatmaps: {}, focus: {}, ms: 0, input: c, stub: true });
  },
};

# Fontes LVGL pre-compiladas

Estas fontes são geradas via [LVGL Font Converter](https://lvgl.io/tools/fontconverter).

## Como gerar (orchestrator+usuário)

Pra cada fonte, ir no Font Converter web:

### VT323

- Baixar TTF: https://fonts.google.com/specimen/VT323 (SIL OFL)
- Para cada tamanho (14, 18, 24, 32, 48):
  - Name: `vt323_<size>`
  - Size: `<size>` px
  - Bpp: `4 bit-per-pixel` (anti-alias smooth)
  - Range: `0x20-0x7F, 0x80-0xFF` (Latin-1 ext, básico)
  - Convert → baixa `vt323_<size>.c` → mover pra `firmware/assets/fonts/`

### Press Start 2P

- Baixar TTF: https://fonts.google.com/specimen/Press+Start+2P (SIL OFL)
- Name: `press_start_24`, Size: 24, Bpp: 1 (pixel-perfect, sem AA), Range: `0x20-0x7E`
- Convert → mover `press_start_24.c` pra `firmware/assets/fonts/`

## platformio.ini

Já está com `build_src_filter = +<src/> +<assets/fonts/>` pra incluir esses .c no build.

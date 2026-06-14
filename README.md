# Trees — Field Guide

A personal botanical record of trees photographed across Taiwan, Japan, and Europe.

**Live site:** https://radihuang.github.io/trees-field-guide/

---

## Stack

- Static HTML / CSS / JS — no framework
- [iNaturalist Vision API](https://api.inaturalist.org/v1/docs/) — species identification
- [Nominatim](https://nominatim.openstreetmap.org/) — reverse geocoding
- [D3.js](https://d3js.org/) — relationship graph
- [Leaflet.js](https://leafletjs.com/) — map view
- GitHub Pages — hosting

---

## 新增照片

### 1. 匯出照片

從 Photos.app 把新的樹照匯出成 JPEG，放入 `photos/` 資料夾。

> 如果是「最佳化儲存空間」模式，匯出時會自動從 iCloud 下載原始檔。

### 2. 讀取 EXIF、地址反查

```bash
python3 scripts/01_prepare.py
```

執行後會：
- 讀取每張照片的 GPS 座標與拍攝日期
- 用 Nominatim 反查英文地址
- 偵測在同一時間、同一地點拍攝的重複照片
- 輸出 `trees.json`（尚無樹種資料）

沒有 GPS 的照片，腳本會標出來，需手動在 `trees.json` 裡填入 `lat` / `lng`。

### 3. 辨識樹種

先取得 iNaturalist API token：前往 https://www.inaturalist.org/users/api_token 登入後複製。

```bash
python3 scripts/02_identify.py <your_inat_api_token>
```

執行後會：
- 對每張照片呼叫 iNaturalist Vision API
- 自動帶入 GPS 座標以提高辨識準確度
- 將學名、英文俗名、信心分數寫入 `trees.json`
- 每次執行只處理尚未辨識的照片（已有資料的會跳過）

### 4. 設為精選

如果想在首頁顯示這張照片，在 `trees.json` 裡找到該筆記錄，把 `featured` 改為 `true`：

```json
{
  "filename": "IMG_xxxx.jpeg",
  "featured": true,
  ...
}
```

### 5. 推上 GitHub

```bash
git add photos/ trees.json
git commit -m "add new specimens"
git push
```

GitHub Pages 約 1 分鐘後自動更新。

---

## 新增文字描述

每筆記錄在 `trees.json` 裡都有一個 `personal_note` 欄位，預設為空字串。

找到你想加描述的照片（用檔名搜尋），填入文字後存檔、推上 GitHub 即可：

```json
{
  "filename": "IMG_1132.jpeg",
  "species_common_en": "Siberian Birch",
  "personal_note": "Photographed at Hakuba ski resort in January. The bare white trunks against the grey winter sky."
}
```

---

## 新增中文名稱

`trees.json` 裡的 `species_common_zh` 欄位可以手動填入或修改中文俗名：

```json
{
  "species_common_zh": "白樺"
}
```

---

## 檔案結構

```
trees-field-guide/
├── index.html          # 主頁面
├── style.css           # 樣式
├── app.js              # 互動邏輯（gallery、modal、圖、地圖）
├── trees.json          # 所有照片的資料（手動維護）
├── photos/             # 壓縮後的 JPEG（1920px / 品質 80）
└── scripts/
    ├── 01_prepare.py   # EXIF 讀取、地址反查、重複偵測
    └── 02_identify.py  # iNaturalist 樹種辨識
```

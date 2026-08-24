/**
 * Enquiry list.
 *
 * The site is statically hosted with no payment processor, so visitors build a
 * list of the products they are interested in and send it as a single enquiry.
 * The list lives in localStorage, which keeps it per-browser and private — it
 * is only ever transmitted when the visitor submits the enquiry form.
 */

export interface EnquiryItem {
  sku: string;
  name: string;
  vialSize: string;
  price: number;
  quantity: number;
}

const KEY = 'vp-enquiry';

/** localStorage throws in some privacy modes; every access is guarded. */
function read(): EnquiryItem[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((i) => i && typeof i.sku === 'string') : [];
  } catch {
    return [];
  }
}

function write(items: EnquiryItem[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(items));
  } catch {
    /* the list simply will not persist across page loads */
  }
  document.dispatchEvent(new CustomEvent('vp:enquiry-changed', { detail: items }));
}

export function getItems(): EnquiryItem[] {
  return read();
}

export function addItem(item: Omit<EnquiryItem, 'quantity'>, quantity = 1): void {
  const items = read();
  const existing = items.find((i) => i.sku === item.sku);
  if (existing) {
    existing.quantity += quantity;
  } else {
    items.push({ ...item, quantity });
  }
  write(items);
}

export function setQuantity(sku: string, quantity: number): void {
  const items = read();
  const target = items.find((i) => i.sku === sku);
  if (!target) return;
  if (quantity <= 0) {
    write(items.filter((i) => i.sku !== sku));
    return;
  }
  target.quantity = quantity;
  write(items);
}

export function removeItem(sku: string): void {
  write(read().filter((i) => i.sku !== sku));
}

export function clear(): void {
  write([]);
}

export function totalQuantity(): number {
  return read().reduce((sum, i) => sum + i.quantity, 0);
}

export function subtotal(): number {
  return read().reduce((sum, i) => sum + i.price * i.quantity, 0);
}

export function formatGBP(pence: number): string {
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(pence);
}

/** Keeps the header badge in sync on every page. */
function refreshBadge(): void {
  const count = totalQuantity();
  document.querySelectorAll<HTMLElement>('[data-enquiry-count]').forEach((el) => {
    el.textContent = String(count);
    el.hidden = count === 0;
  });
}

/** Wires up every "add to enquiry" button on the page. */
function bindAddButtons(): void {
  document.querySelectorAll<HTMLButtonElement>('[data-add-to-enquiry]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const { sku, name, vialSize, price } = btn.dataset;
      if (!sku || !name) return;
      addItem({ sku, name, vialSize: vialSize ?? '', price: Number(price ?? 0) });

      const original = btn.dataset.label ?? btn.textContent ?? 'Add to enquiry';
      btn.dataset.label = original;
      btn.textContent = 'Added ✓';
      btn.classList.add('is-added');
      window.setTimeout(() => {
        btn.textContent = original;
        btn.classList.remove('is-added');
      }, 1600);
    });
  });
}

document.addEventListener('vp:enquiry-changed', refreshBadge);
refreshBadge();
bindAddButtons();

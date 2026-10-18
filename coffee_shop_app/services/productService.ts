import { Product } from '../types/types';
import axios from 'axios';
import { getSupabase } from '../config/supabaseConfig';

const productsApiUrl = process.env.EXPO_PUBLIC_PRODUCTS_API_URL as string;

// Products come from the API when EXPO_PUBLIC_PRODUCTS_API_URL is set (local development),
// otherwise from the Supabase `products` table (filled by `python -m supabase_seed`).
const fetchProducts = async (): Promise<Product[]> => {
  if (productsApiUrl) {
    const response = await axios.get<Product[]>(`${productsApiUrl.replace(/\/+$/, '')}/products`);
    return response.data;
  }

  const { data, error } = await getSupabase()
    .from('products')
    .select('name, category, description, price, rating, image_url')
    .order('sort_order');
  if (error) throw error;
  return (data ?? []).map((row) => ({ ...row, id: row.name, price: Number(row.price), rating: Number(row.rating) }));
};

export { fetchProducts };

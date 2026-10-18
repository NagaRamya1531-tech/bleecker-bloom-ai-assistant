// Products Interface
export interface Product {
    id: string;
    category: string;
    description: string;
    image_url: string;
    name: string;
    price: number;
    rating: number;
  }

export interface ProductCategory {
    id: string;
    selected: boolean;
}

// Knowledge base section a chatbot answer was grounded in
export interface MessageSource {
    id: string;
    title: string;
    section: string;
}

// Item suggested by the recommendation engine
export interface Recommendation {
    name: string;
    category: string;
    price: number;
    description: string;
    reason: string;
}

// Order recorded by the API at checkout (prices come from the server's menu)
export interface PlacedOrder {
    id: string;
    items: { item: string; quantity: number; price: number }[];
    total: number;
    created_at: number;
}

// Message Interface
export interface MessageInterface {
    role: string;
    content: string;
    memory?: any;
}
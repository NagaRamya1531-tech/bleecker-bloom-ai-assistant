import axios from 'axios';
import { MessageInterface, PlacedOrder } from '@/types/types';
import { API_KEY, API_URL } from '@/config/runpodConfigs';
import { getIdentityHeaders } from '@/services/identity';

const baseUrl = (API_URL || '').replace(/\/+$/, '');

// The local/FastAPI server keeps conversations and orders per customer. A RunPod
// serverless endpoint only has the stateless handler, so the app falls back to
// sending the whole conversation and keeps it in memory.
const supportsSessions = !/runpod/i.test(baseUrl);

const sessionRequest = async <T>(method: 'get' | 'post' | 'delete', path: string, data?: unknown): Promise<T> => {
    const response = await axios.request<T>({
        method,
        url: `${baseUrl}${path}`,
        data,
        headers: { 'Content-Type': 'application/json', ...(await getIdentityHeaders()) },
    });
    return response.data;
};

type CartLine = { item: string; quantity: number };

// The app's cart as order lines; sent with each message so the Order Taking Agent
// keeps items added outside the chat. The server re-prices them from the menu.
const cartLines = (cart: { [item: string]: number }): CartLine[] =>
    Object.entries(cart)
        .filter(([, quantity]) => quantity > 0)
        .map(([item, quantity]) => ({ item, quantity }));

// Stateless call (RunPod): the client sends the whole conversation.
async function callChatBotAPI(messages: MessageInterface[], cart: CartLine[]): Promise<MessageInterface> {
    try {
        const response = await axios.post(API_URL, {
            input: { messages, cart }
        }, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${API_KEY}`
            }
        });

        let output = response.data;
        let outputMessage: MessageInterface = output['output'];

        return outputMessage;
    } catch (error) {
        console.error('Error calling the API:', error);
        throw error;
    }
}

// Stateful calls: the server stores the conversation, so only the new message is sent.
const fetchConversation = async (): Promise<MessageInterface[]> =>
    (await sessionRequest<{ messages: MessageInterface[] }>('get', '/chat')).messages;

const sendChatMessage = async (message: string, cart: CartLine[]): Promise<MessageInterface> =>
    (await sessionRequest<{ output: MessageInterface }>('post', '/chat', { message, cart })).output;

const resetConversation = async (): Promise<void> => {
    await sessionRequest('delete', '/chat');
};

// Prices are recomputed by the server from the menu; the app only sends names and quantities.
const placeOrder = async (cart: { [item: string]: number }): Promise<PlacedOrder> =>
    sessionRequest<PlacedOrder>('post', '/orders', { items: cartLines(cart) });

export { callChatBotAPI, cartLines, fetchConversation, placeOrder, resetConversation, sendChatMessage, supportsSessions };

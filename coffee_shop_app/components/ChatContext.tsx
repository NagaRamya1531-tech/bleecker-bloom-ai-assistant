import React, { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useCart } from '@/components/CartContext';
import {
  callChatBotAPI,
  cartLines,
  fetchConversation,
  resetConversation,
  sendChatMessage,
  supportsSessions,
} from '@/services/chatBot';
import { MessageInterface } from '@/types/types';

export const GREETING: MessageInterface = {
  role: 'assistant',
  content: "Hi, welcome to Bleecker & Bloom. I can help you find a drink, check the menu, or put an order together.",
};

interface ChatContextType {
  messages: MessageInterface[];
  isTyping: boolean;
  sendMessage: (text: string) => Promise<void>;
  startNewChat: (options?: { alreadyClearedOnServer?: boolean }) => Promise<void>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

// One conversation shared by the chat popup and the full chat screen. With the
// session API, the server stores it (Supabase), so it is restored on app start.
export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const { cartItems, addToCart, emptyCart } = useCart();
  const [messages, setMessages] = useState<MessageInterface[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const messagesRef = useRef<MessageInterface[]>([]);
  messagesRef.current = messages;
  const cartRef = useRef(cartItems);
  cartRef.current = cartItems;

  // The Order Taking Agent owns the cart; mirror its latest order into the app's cart.
  const syncCart = useCallback((history: MessageInterface[]) => {
    const latestOrder = [...history].reverse().find((message) => message.memory?.order)?.memory.order;
    if (!latestOrder) return;
    emptyCart();
    latestOrder.forEach((item: { item: string; quantity: number }) => addToCart(item.item, item.quantity));
  }, [addToCart, emptyCart]);

  useEffect(() => {
    if (!supportsSessions) return;
    fetchConversation()
      .then((history) => {
        setMessages(history);
        syncCart(history);
      })
      .catch((error) => console.warn('Could not restore the conversation:', error?.message));
    // Restore once, when the app starts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    const content = text.trim();
    if (!content || isTyping) return;

    const userMessage: MessageInterface = { role: 'user', content };
    const history = [...messagesRef.current, userMessage];
    setMessages(history);
    setIsTyping(true);
    try {
      // Send the current cart so items added from the menu screens aren't lost when the agent replies.
      const cart = cartLines(cartRef.current);
      const reply = supportsSessions ? await sendChatMessage(content, cart) : await callChatBotAPI(history, cart);
      setMessages((current) => [...current, reply]);
      syncCart([reply]);
    } catch {
      setMessages((current) => [
        ...current,
        { role: 'assistant', content: "I'm having trouble connecting right now. Please try again in a moment." },
      ]);
    } finally {
      setIsTyping(false);
    }
  }, [isTyping, syncCart]);

  const startNewChat = useCallback(async (options?: { alreadyClearedOnServer?: boolean }) => {
    if (supportsSessions && !options?.alreadyClearedOnServer) {
      await resetConversation().catch((error) => console.warn('Could not reset the conversation:', error?.message));
    }
    setMessages([]);
  }, []);

  return (
    <ChatContext.Provider value={{ messages, isTyping, sendMessage, startNewChat }}>
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = (): ChatContextType => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};

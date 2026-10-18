import Feather from '@expo/vector-icons/Feather';
import { router, usePathname } from 'expo-router';
import React, { useEffect, useRef, useState } from 'react';
import {
  Pressable,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import { GREETING, useChat } from '@/components/ChatContext';
import MessageSources from '@/components/MessageSources';
import RecommendationChips from '@/components/RecommendationChips';

const AUTO_OPEN_DELAY_MS = 30_000;

const ChatPopup = () => {
  const pathname = usePathname();
  const { width, height } = useWindowDimensions();
  const { messages: conversation, isTyping, sendMessage: send, startNewChat } = useChat();
  const messages = [GREETING, ...conversation];
  const [isOpen, setIsOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const hasInteracted = useRef(false);
  const hasAutoOpened = useRef(false);
  const scrollViewRef = useRef<ScrollView>(null);
  const isChatScreen = pathname.endsWith('/chatRoom');
  const panelWidth = Math.min(width - 24, 380);
  const panelHeight = Math.min(height - 112, 540);

  useEffect(() => {
    if (isChatScreen || hasAutoOpened.current || hasInteracted.current) return;

    const timeout = setTimeout(() => {
      hasAutoOpened.current = true;
      setIsOpen(true);
    }, AUTO_OPEN_DELAY_MS);

    return () => clearTimeout(timeout);
  }, [isChatScreen]);

  const openPopup = () => {
    hasInteracted.current = true;
    setIsOpen(true);
  };

  const minimizePopup = () => {
    hasInteracted.current = true;
    setIsOpen(false);
  };

  const openFullChat = () => {
    hasInteracted.current = true;
    setIsOpen(false);
    router.push('/(tabs)/chatRoom');
  };

  const sendMessage = (suggestedMessage?: string) => {
    const content = (suggestedMessage ?? draft).trim();
    if (!content || isTyping) return;
    setDraft('');
    send(content);
  };

  if (isChatScreen) return null;

  return (
    <View pointerEvents="box-none" style={{ position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, zIndex: 1000 }}>
      {isOpen ? (
        <View
          className="overflow-hidden rounded-lg border border-app_line bg-app_cream"
          style={{
            position: 'absolute',
            right: 12,
            bottom: 78,
            width: panelWidth,
            height: panelHeight,
            maxHeight: 540,
            elevation: 16,
            shadowColor: '#000',
            shadowOpacity: 0.2,
            shadowRadius: 18,
            shadowOffset: { width: 0, height: 8 },
          }}
        >
          <View className="flex-row items-center justify-between bg-app_ink px-4 py-3">
            <View>
              <Text className="text-white text-base font-[Sora-SemiBold]">Bleecker & Bloom</Text>
              <Text className="mt-0.5 text-app_leaf text-xs font-[Sora-Regular]">Your neighborhood barista</Text>
            </View>
            <View className="flex-row items-center">
              {conversation.length > 0 && (
                <TouchableOpacity onPress={() => startNewChat()} accessibilityLabel="Start a new chat" className="p-2">
                  <Feather name="refresh-cw" size={16} color="white" />
                </TouchableOpacity>
              )}
              <TouchableOpacity onPress={openFullChat} accessibilityLabel="Open full chat" className="p-2">
                <Feather name="maximize-2" size={17} color="white" />
              </TouchableOpacity>
              <TouchableOpacity onPress={minimizePopup} accessibilityLabel="Minimize chat" className="p-2">
                <Feather name="chevron-down" size={21} color="white" />
              </TouchableOpacity>
            </View>
          </View>

          <ScrollView
            ref={scrollViewRef}
            className="flex-1 px-3 pt-3"
            contentContainerStyle={{ gap: 10, paddingBottom: 12 }}
            onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
          >
            {messages.map((message, index) => {
              const isUser = message.role === 'user';
              return (
                <View key={`${index}-${message.role}`} className={`w-full ${isUser ? 'items-end' : 'items-start'}`}>
                  <View className={`max-w-[88%] rounded-lg px-3 py-2 ${isUser ? 'bg-app_ink' : 'border border-app_line bg-white'}`}>
                    <Text className={`text-xs leading-5 font-[Sora-Regular] ${isUser ? 'text-white' : 'text-app_ink'}`}>
                      {message.content}
                    </Text>
                    {!isUser && <MessageSources sources={message.memory?.sources} />}
                  </View>
                  {!isUser && index === messages.length - 1 && !isTyping && (
                    <RecommendationChips recommendations={message.memory?.recommendations} onAdd={sendMessage} />
                  )}
                </View>
              );
            })}
            {isTyping && <Text className="px-2 text-xs text-[#68746B] font-[Sora-Regular]">Brewing a reply...</Text>}
          </ScrollView>

          {messages.length === 1 && (
            <View className="flex-row gap-2 px-3 pb-2">
              <Pressable onPress={() => sendMessage('What are your opening hours?')} className="rounded-full border border-app_line bg-white px-3 py-2">
                <Text className="text-app_ink text-xs font-[Sora-SemiBold]">Shop hours</Text>
              </Pressable>
              <Pressable onPress={() => sendMessage('What is on the menu?')} className="rounded-full border border-app_line bg-white px-3 py-2">
                <Text className="text-app_ink text-xs font-[Sora-SemiBold]">The menu</Text>
              </Pressable>
            </View>
          )}

          <View className="flex-row items-center gap-2 border-t border-app_line bg-white px-3 py-2">
            <TextInput
              value={draft}
              onChangeText={setDraft}
              onSubmitEditing={() => sendMessage()}
              editable={!isTyping}
              returnKeyType="send"
              placeholder="Ask the barista..."
              placeholderTextColor="#77796F"
              accessibilityLabel="Message the Bleecker & Bloom barista"
              className="h-10 flex-1 px-2 text-app_ink text-sm font-[Sora-Regular]"
            />
            <TouchableOpacity
              onPress={() => sendMessage()}
              disabled={!draft.trim() || isTyping}
              accessibilityLabel="Send message"
              className={`h-10 w-10 items-center justify-center rounded-full ${draft.trim() && !isTyping ? 'bg-app_orange_color' : 'bg-[#C9CCC3]'}`}
            >
              <Feather name="arrow-up" size={19} color="white" />
            </TouchableOpacity>
          </View>
        </View>
      ) : (
        <TouchableOpacity
          onPress={openPopup}
          accessibilityLabel="Open Bleecker & Bloom chat"
          style={{ position: 'absolute', right: 16, bottom: 82, elevation: 14 }}
          className="h-14 w-14 items-center justify-center rounded-full bg-app_ink"
        >
          <Feather name="message-circle" size={23} color="white" />
        </TouchableOpacity>
      )}
    </View>
  );
};

export default ChatPopup;
import { ScrollView,View} from 'react-native'
import React, { useRef, useEffect } from 'react'
import MessageItem from './MessageItem';
import { MessageInterface } from '@/types/types';
import TypingIndicator from '@/components/TypingIndicator';

interface MessageListProps {
  messages: MessageInterface[];
  isTyping: boolean;
  onSuggestionPress?: (message: string) => void;
}

const MessageList = ({messages,isTyping = false,onSuggestionPress}:MessageListProps) => {

  const scrollViewRef =  useRef<ScrollView | null>(null)
  // Scroll to bottom when messages change
  useEffect(() => {
    scrollViewRef.current?.scrollToEnd({ animated: true })
  }, [messages])

  return (
    <ScrollView
      ref={scrollViewRef}
      showsVerticalScrollIndicator={false}
      contentContainerStyle={{paddingTop: 16, paddingBottom: 12}}
    >
      {
        messages.map((message, index) => (
          <MessageItem
            key={index}
            message={message}
            // Only the latest reply's suggestions are tappable.
            onSuggestionPress={index === messages.length - 1 && !isTyping ? onSuggestionPress : undefined}
          />
        ))
      }
    
      {isTyping && (
          <View className="w-[80%] ml-3 mb-3">
            <View className="flex self-start p-3 px-4 rounded-2xl bg-white border border-app_line">
              <TypingIndicator />
            </View>
          </View>
      )}

            
    </ScrollView>
  )
}

export default MessageList
import { Alert, ScrollView, TouchableOpacity, View,Text } from 'react-native'
import React, { useRef } from 'react'
import { StatusBar } from 'expo-status-bar'
import MessageList  from '@/components/MessageList'
import { widthPercentageToDP as wp, heightPercentageToDP as hp } from 'react-native-responsive-screen'
import { GestureHandlerRootView, TextInput } from 'react-native-gesture-handler'
import { Feather } from '@expo/vector-icons'
import PageHeader from '@/components/PageHeader'
import { GREETING, useChat } from '@/components/ChatContext'

const ChatRoom = () => {
  const { messages, isTyping, sendMessage, startNewChat } = useChat();
  const textRef = useRef('')
  const inputRef = useRef<TextInput>(null)

    const handleSendMessage = (suggestedMessage?: string) => {
        const message = (suggestedMessage ?? textRef.current).trim();
        if (!message || isTyping) return;
        textRef.current = ''
        inputRef?.current?.clear();
        sendMessage(message);
    }

    const confirmNewChat = () => {
        Alert.alert('Start a new chat?', 'This clears the conversation. Your bag stays as it is.', [
            { text: 'Cancel', style: 'cancel' },
            { text: 'New chat', onPress: () => startNewChat() },
        ]);
    }

  return (
    <GestureHandlerRootView>
        <StatusBar style='dark' />
        
        <View
            className='flex-1 bg-white'
        >

                <PageHeader title="Ask the barista" showHeaderRight={false} bgColor='#F5F3E9'/>
        
                <View className='h-px bg-app_line' />

                {messages.length > 0 && (
                    <TouchableOpacity onPress={confirmNewChat} accessibilityLabel="Start a new chat" className="flex-row items-center self-end px-4 py-2">
                        <Feather name="refresh-cw" size={13} color="#68746B" />
                        <Text className="ml-1 text-[#68746B] text-xs font-[Sora-SemiBold]">New chat</Text>
                    </TouchableOpacity>
                )}

                {messages.length === 0 && (
                    <View className="bg-app_cream py-3">
                        <Text className="px-4 mb-2 text-[#68746B] text-xs font-[Sora-SemiBold]">A GOOD PLACE TO START</Text>
                        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingHorizontal: 16, gap: 8 }}>
                            <TouchableOpacity onPress={() => handleSendMessage('What are your opening hours?')} className="px-4 py-2 bg-white border border-app_line rounded-full">
                                <Text className="text-app_ink text-xs font-[Sora-SemiBold]">Shop hours</Text>
                            </TouchableOpacity>
                            <TouchableOpacity onPress={() => handleSendMessage('What is on the menu?')} className="px-4 py-2 bg-white border border-app_line rounded-full">
                                <Text className="text-app_ink text-xs font-[Sora-SemiBold]">The menu</Text>
                            </TouchableOpacity>
                            <TouchableOpacity onPress={() => handleSendMessage('Help me place an order.')} className="px-4 py-2 bg-white border border-app_line rounded-full">
                                <Text className="text-app_ink text-xs font-[Sora-SemiBold]">Build an order</Text>
                            </TouchableOpacity>
                        </ScrollView>
                    </View>
                )}

        <View
            className='flex-1 justify-between bg-app_cream overflow-hidden'
        >
            <View
                className='flex-1'
            >
                <MessageList 
                    messages={[GREETING, ...messages]}
                    isTyping={isTyping}
                    onSuggestionPress={handleSendMessage}
                />
            </View>

            <View
                style={{marginBottom: hp(2.7)}}
                className='pt-2'
            >
                <View
                    className="flex-row mx-3 justify-between border p-2 bg-white border-app_line rounded-full pl-4"
                >
                    <TextInput 
                        ref = {inputRef}
                        onChangeText={value => textRef.current = value}
                        placeholder='Ask about coffee, the menu, or ordering'
                        placeholderTextColor="#77796F"
                        style={{fontSize: hp(2)}}
                        className='flex-1 mr2'
                    />
                    <TouchableOpacity
                        onPress = {() => handleSendMessage()}
                        className='bg-app_orange_color p-2 mr-[1px] rounded-full'
                        disabled={isTyping}
                    >
                        <Feather name="send" size={hp(2.5)} color="white"/>
                    </TouchableOpacity>
                </View>
            </View>
        </View>



        </View>
    </GestureHandlerRootView>
  )
}

export default ChatRoom


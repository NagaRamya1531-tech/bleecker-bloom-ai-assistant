import { Text, View } from 'react-native'
import React from 'react'
import { heightPercentageToDP } from 'react-native-responsive-screen';
import { MessageInterface } from '@/types/types';
import MessageSources from './MessageSources';
import RecommendationChips from './RecommendationChips';

interface Message {
    message: MessageInterface;
    onSuggestionPress?: (message: string) => void;
}

const MessageItem = ({message, onSuggestionPress}:Message) => {
  if (message?.role == 'user') {
    return (
        <View
            className='flex-row justify-end  mb-3 mr-3'
        >
            <View className='w-80%'>
                <View className='self-end max-w-[94%] p-3 rounded-2xl bg-app_ink'>
                    <Text 
                        className="text-white font-[Sora-Regular]"
                        style = {{fontSize: heightPercentageToDP(1.9)}}>
                        {message?.content}
                    </Text>
                </View>
            </View>

        </View>
    )
  } else {
    return (
        <View
            className='w-[80%] ml-3 mb-3'
        >
            <View className='flex self-start p-3 px-4 rounded-2xl bg-white border border-app_line'>
                <Text className="mb-1 text-app_orange_color text-[10px] font-[Sora-SemiBold]">B&B BARISTA</Text>
                <Text
                    className="text-app_ink font-[Sora-Regular]"
                    style = {{fontSize: heightPercentageToDP(1.9)}}
                >
                    {message?.content}
                </Text>
                <MessageSources sources={message?.memory?.sources} />
            </View>
            <RecommendationChips recommendations={message?.memory?.recommendations} onAdd={onSuggestionPress} />

        </View>
    )
  }
}

export default MessageItem
import { Text, View } from 'react-native'
import React from 'react'
import { TouchableOpacity,GestureHandlerRootView } from 'react-native-gesture-handler'
import {router} from "expo-router";

const ThankyouPage = () => {
  return (
    <GestureHandlerRootView>
        <View className='w-full h-full items-center justify-center '>
        <Text className='text-4xl text-app_ink text-center mx-10' style={{ fontFamily: 'Georgia' }}>Thanks, neighbor.</Text>
        <Text className='mt-3 text-base text-[#68746B] text-center mx-10 font-[Sora-Regular]'>We’re glad you stopped by Bleecker & Bloom.</Text>

        <TouchableOpacity 
                className='bg-app_ink rounded-lg items-center justify-center mt-6 py-3 px-5 font-[Sora-SemiBold]'
                onPress={() => router.push("/(tabs)/home")}
              >
                <Text className="text-base text-white font-[Sora-SemiBold]">Back to the counter</Text>
          </TouchableOpacity> 
        </View>
    </GestureHandlerRootView>
  )
}

export default ThankyouPage
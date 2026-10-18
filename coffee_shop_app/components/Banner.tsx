import {Text, ImageBackground, View } from 'react-native'
import React from 'react'

const Banner = () => {
  return (
    <View className="mx-5 mt-5">
      <ImageBackground
        source={require('../assets/images/banner.png')}
        resizeMode="cover"
        imageStyle={{ width: '100%', height: '100%', borderRadius: 12 }}
        className="h-36 justify-center overflow-hidden rounded-xl"
      >
        <View className="ml-4 w-[57%]">
          <Text className="text-app_ink text-xs font-[Sora-SemiBold]">
            A LITTLE PAUSE, CLOSE TO HOME
          </Text>
          <Text
            className="mt-2 text-app_ink text-2xl font-[Sora-SemiBold]"
            style={{ lineHeight: 31 }}
          >
            Make room for a ritual.
          </Text>
          <Text className="mt-1 text-app_ink text-xs font-[Sora-Regular]">
            Coffee, pastries, and something sweet.
          </Text>
        </View>
      </ImageBackground>
    </View>
  )
}

export default Banner
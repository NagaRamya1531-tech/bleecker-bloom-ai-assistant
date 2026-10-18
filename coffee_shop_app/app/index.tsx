/// <reference types="nativewind/types" />
import { Text, View, SafeAreaView, ImageBackground, StyleSheet, useWindowDimensions } from "react-native";
import { GestureHandlerRootView, TouchableOpacity } from "react-native-gesture-handler";
import {router} from "expo-router";
import { Feather } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';


export default function Index() {
  const { width } = useWindowDimensions();
  const isWideScreen = width >= 760;
  const brandCopy = (
    <>
      <View>
        <Text className={`${isWideScreen ? 'text-base' : 'text-xs'} text-app_leaf font-[Sora-SemiBold]`}>
          GREENWICH VILLAGE | NEW YORK
        </Text>
        <Text
          className={`mt-5 text-white ${isWideScreen ? 'text-8xl' : 'text-5xl'}`}
          style={{ fontFamily: 'Georgia', lineHeight: isWideScreen ? 96 : 58 }}
        >
          Bleecker{'\n'}& Bloom
        </Text>
      </View>

      <View className="w-[92%]">
        <Text className={`text-white ${isWideScreen ? 'text-5xl' : 'text-2xl'} font-[Sora-SemiBold]`}>
          Coffee for the walk. A table when you stay.
        </Text>
        <Text className={`mt-3 text-app_cream ${isWideScreen ? 'text-2xl' : 'text-base'} font-[Sora-Regular]`}>
          Espresso, pastries, and a little pause in the neighborhood.
        </Text>
        <TouchableOpacity
          className={`mt-7 flex-row items-center justify-between rounded-lg bg-app_cream ${isWideScreen ? 'px-6 py-5' : 'px-5 py-4'}`}
          onPress={() => router.push('/(tabs)/home')}
        >
          <Text className={`text-app_ink ${isWideScreen ? 'text-xl' : 'text-base'} font-[Sora-SemiBold]`}>Explore the counter</Text>
          <Feather name="arrow-right" size={20} color="#203B32" />
        </TouchableOpacity>
      </View>
    </>
  );

  return (
    <GestureHandlerRootView className="flex-1">
      <SafeAreaView className="flex-1">
        <ImageBackground
          className="flex-1"
          source={isWideScreen
            ? require('../assets/images/welcome_image.jpg')
            : require('../assets/images/index_bg_image.png')}
          resizeMode="cover"
          imageStyle={{ width: '100%', height: '100%' }}
        >
          {isWideScreen && (
            <LinearGradient
              colors={['rgba(8, 11, 9, 0.76)', 'rgba(8, 11, 9, 0.52)', 'rgba(8, 11, 9, 0)']}
              locations={[0, 0.64, 1]}
              start={{ x: 0, y: 0.5 }}
              end={{ x: 1, y: 0.5 }}
              pointerEvents="none"
              style={[StyleSheet.absoluteFillObject, { width: '72%' }]}
            />
          )}
          <View
            className={`flex-1 justify-between ${isWideScreen ? 'px-10 py-10 w-[56%]' : 'px-7 pt-12 pb-8 w-full'}`}
            style={isWideScreen ? { maxWidth: 720 } : undefined}
          >
            {brandCopy}
          </View>
        </ImageBackground>
      </SafeAreaView>
    </GestureHandlerRootView>
  );
}
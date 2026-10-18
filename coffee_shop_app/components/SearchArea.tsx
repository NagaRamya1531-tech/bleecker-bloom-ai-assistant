import {Pressable, Text, TextInput, View } from 'react-native'
import React from 'react'
import Feather from '@expo/vector-icons/Feather';
import { router } from 'expo-router';

interface SearchAreaProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

const SearchArea = ({ searchQuery, onSearchChange }: SearchAreaProps) => {
  return (
    <View
        className='w-full items-center bg-app_ink pb-7'>
        <View className='w-[90%] pt-7'>
        <View className='flex-row justify-between items-center'>
          <Pressable
            onPress={() => router.push('/')}
            accessibilityRole="button"
            accessibilityLabel="Return to welcome page"
            className="flex-row items-center gap-2"
          >
            <Feather name="arrow-left" size={17} color="#F5F3E9" />
            <Text className='text-app_cream text-base font-[Sora-SemiBold]'>
              Welcome
            </Text>
          </Pressable>
          <View className="flex-row items-center gap-2">
            <Text className='text-app_cream text-sm font-[Sora-SemiBold]'>Bleecker & Bloom</Text>
            <Feather name="map-pin" size={17} color="#A9B98B" />
          </View>
        </View>
        <Text className='mt-5 text-app_leaf text-xs font-[Sora-SemiBold]'>
            YOUR NEIGHBORHOOD COFFEE SHOP
        </Text>
        <Text className='mt-1 text-white text-2xl font-[Sora-SemiBold]'>
            Greenwich Village
        </Text>
        <Text className='text-app_cream text-sm font-[Sora-Regular]'>
            New York City
        </Text>

        <View className="w-full mt-5 h-12 flex-row items-center px-4 bg-white rounded-lg">
          <Feather name="search" size={19} color="#203B32" />
          <TextInput
            value={searchQuery}
            onChangeText={onSearchChange}
            placeholder="Search coffee, pastries..."
            placeholderTextColor="#77796F"
            className="flex-1 ml-3 text-app_ink font-[Sora-Regular]"
            accessibilityLabel="Search the menu"
          />
        </View>
        </View>
    </View>
  )
}

export default SearchArea
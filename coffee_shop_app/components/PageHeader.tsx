import React from 'react';
import { Text, TouchableOpacity } from 'react-native';
import { FontAwesome5, Feather } from '@expo/vector-icons';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { router, Stack } from 'expo-router';

interface HeaderProps {
    title: string;
    showHeaderRight: boolean;
    bgColor:string;
}

const PageHeader: React.FC<HeaderProps> = ({ title, showHeaderRight,bgColor }) => {
    return (
        <Stack.Screen
            options={{
                headerShadowVisible: false,
                headerStyle: {
                    backgroundColor: bgColor,
                },
                headerTitleAlign: 'center',
                headerTitle: () => (
                    <Text className='text-lg text-app_ink font-[Sora-SemiBold]'>
                        {title}
                    </Text>
                ),
                headerRight: showHeaderRight
                    ? () => (
                            <FontAwesome5
                                style={{ marginRight: 10 }}
                                name="heart"
                                size={24}
                                color="#203B32"
                            />
                        )
                    : undefined,
                headerBackVisible: false,
                headerLeft: () => (
                    <GestureHandlerRootView className='flex-row items-center gap-4'>
                        <TouchableOpacity className='pl-2' onPress={() => router.back()}>
                            <Feather name="arrow-left" size={22} color="#203B32" />
                        </TouchableOpacity>
                    </GestureHandlerRootView>
                ),
            }}
        />
    );
};

export default PageHeader;
import { Text } from 'react-native'
import React from 'react'
import { MessageSource } from '@/types/types';

interface MessageSourcesProps {
    sources?: MessageSource[];
}

// Shows which knowledge base sections the Details Agent answered from.
const MessageSources = ({sources}: MessageSourcesProps) => {
  if (!sources?.length) return null;

  const labels = [...new Set(sources.map((source) =>
    source.section === source.title ? source.title : `${source.title} · ${source.section}`
  ))].slice(0, 3);

  return (
    <Text className="mt-2 text-[10px] text-[#68746B] font-[Sora-Regular]">
      Sources: {labels.join(', ')}
    </Text>
  )
}

export default MessageSources

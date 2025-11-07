// 图片预览弹窗组件

import './ImagePreviewModal.css'

interface ImagePreviewModalProps {
  imageUrl: string
  isOpen: boolean
  onClose: () => void
}

function ImagePreviewModal({ imageUrl, isOpen, onClose }: ImagePreviewModalProps) {
  if (!isOpen) return null

  return (
    <div className="image-modal-overlay" onClick={onClose}>
      <div className="image-modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="image-modal-close" onClick={onClose}>×</button>
        <img src={imageUrl} alt="地图预览" className="preview-image" />
      </div>
    </div>
  )
}

export default ImagePreviewModal


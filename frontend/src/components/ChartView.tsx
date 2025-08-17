import React from 'react'

export default function ChartView({src}:{src:string}){
  return <img src={src.startsWith('http')?src:(import.meta as any).env.VITE_API_BASE + '/' + src.replace(/^\.\//,'')} alt="chart" style={{maxWidth:'100%'}}/>
}
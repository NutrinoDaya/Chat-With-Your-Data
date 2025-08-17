import React from 'react'

export default function TableView({columns, rows}:{columns:string[], rows:any[][]}){
  return (
    <table border={1} cellPadding={6} style={{borderCollapse:'collapse', width:'100%'}}>
      <thead>
        <tr>{columns.map(c=> <th key={c} style={{textAlign:'left'}}>{c}</th>)}</tr>
      </thead>
      <tbody>
        {rows.map((r,i)=> (
          <tr key={i}>{r.map((v,j)=> <td key={j}>{String(v)}</td>)}</tr>
        ))}
      </tbody>
    </table>
  )
}